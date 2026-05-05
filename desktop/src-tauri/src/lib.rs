// Tauri shell that spawns the FastAPI sidecar and exposes its port to the
// webview. In debug builds we run the sidecar straight from the project venv
// for fast iteration; release builds use the PyInstaller-built binary that
// `desktop/scripts/build-sidecar.sh` writes into Contents/MacOS/.

use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

#[cfg(unix)]
use std::os::unix::process::CommandExt;

use tauri::{Manager, RunEvent, State};

struct SidecarChild(Mutex<Option<Child>>);

struct SidecarPort(u16);

#[tauri::command]
fn get_sidecar_port(state: State<'_, SidecarPort>) -> u16 {
    state.0
}

fn pick_free_port() -> std::io::Result<u16> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let port = listener.local_addr()?.port();
    drop(listener);
    Ok(port)
}

fn repo_root() -> PathBuf {
    // src-tauri/src/lib.rs → repo root is two parents up from CARGO_MANIFEST_DIR
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or(manifest_dir)
}

fn build_command(port: u16, app_data_dir: &PathBuf) -> Command {
    let port_str = port.to_string();
    let dir_str = app_data_dir.to_string_lossy().to_string();

    let mut cmd: Command;
    if cfg!(debug_assertions) {
        // Dev: invoke the module via the project venv.
        let root = repo_root();
        let python = root.join(".venv/bin/python");
        eprintln!(
            "spawning dev sidecar: {} -m tube_agent.cli_sidecar --port {} --app-data-dir {}",
            python.display(),
            port_str,
            dir_str
        );
        cmd = Command::new(&python);
        cmd.current_dir(&root)
            .args(["-m", "tube_agent.cli_sidecar"]);
    } else {
        // Release: PyInstaller-built sidecar lives next to the main binary
        // inside the .app bundle (Contents/MacOS/tube-agent-sidecar).
        let exe = std::env::current_exe().expect("could not resolve current_exe");
        let bin = exe
            .parent()
            .map(|p| p.join("tube-agent-sidecar"))
            .unwrap_or_else(|| PathBuf::from("tube-agent-sidecar"));
        cmd = Command::new(bin);
    }

    cmd.args(["--port", &port_str, "--app-data-dir", &dir_str])
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    // Put the sidecar in its own process group so we can SIGTERM the entire
    // group on quit. PyInstaller's --onefile bootstrap spawns a child Python
    // interpreter; without a group kill, that child outlives the parent.
    #[cfg(unix)]
    {
        cmd.process_group(0);
    }
    cmd
}

fn spawn_sidecar(port: u16, app_data_dir: &PathBuf) -> std::io::Result<Child> {
    build_command(port, app_data_dir).spawn()
}

#[cfg(unix)]
fn terminate_sidecar(child: &mut Child) {
    let pid = child.id() as i32;
    // Negative PID targets the whole process group, killing both the
    // PyInstaller bootstrap and the actual Python interpreter beneath it.
    unsafe {
        libc::kill(-pid, libc::SIGTERM);
    }
    // Give it a moment to exit gracefully, then escalate.
    for _ in 0..20 {
        if let Ok(Some(_)) = child.try_wait() {
            return;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    unsafe {
        libc::kill(-pid, libc::SIGKILL);
    }
    let _ = child.wait();
}

#[cfg(not(unix))]
fn terminate_sidecar(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let app_data_dir = app
                .path()
                .app_data_dir()
                .expect("could not resolve app data dir");
            std::fs::create_dir_all(&app_data_dir)?;

            let port = pick_free_port()?;
            let child = spawn_sidecar(port, &app_data_dir)?;

            let pid = child.id();
            app.manage(SidecarPort(port));
            app.manage(SidecarChild(Mutex::new(Some(child))));
            eprintln!(
                "sidecar pid={} port={} app_data_dir={}",
                pid,
                port,
                app_data_dir.display()
            );
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_sidecar_port])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                if let Some(state) = app_handle.try_state::<SidecarChild>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            terminate_sidecar(&mut child);
                        }
                    }
                }
            }
        });
}
