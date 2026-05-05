// Tauri shell that spawns the FastAPI sidecar and exposes its port to the
// webview. In debug builds we run the sidecar straight from the project venv
// for fast iteration; release builds expect the PyInstaller-built bundle on
// disk (see desktop/scripts/build-sidecar.sh).

use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

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

fn spawn_sidecar(port: u16, app_data_dir: &PathBuf) -> std::io::Result<Child> {
    let port_str = port.to_string();
    let dir_str = app_data_dir.to_string_lossy().to_string();

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
        Command::new(&python)
            .current_dir(&root)
            .args([
                "-m",
                "tube_agent.cli_sidecar",
                "--port",
                &port_str,
                "--app-data-dir",
                &dir_str,
            ])
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
    } else {
        // Release: PyInstaller-built sidecar lives next to the bundled
        // resources. Tauri exposes the binary path via env var when bundled
        // through `bundle.externalBin`, but we resolve manually here.
        let exe = std::env::current_exe()?;
        let bin = exe
            .parent()
            .map(|p| p.join("tube-agent-sidecar"))
            .unwrap_or_else(|| PathBuf::from("tube-agent-sidecar"));
        Command::new(bin)
            .args([
                "--port",
                &port_str,
                "--app-data-dir",
                &dir_str,
            ])
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
    }
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

            app.manage(SidecarPort(port));
            app.manage(SidecarChild(Mutex::new(Some(child))));
            eprintln!(
                "sidecar pid={} port={} app_data_dir={}",
                app.state::<SidecarChild>()
                    .0
                    .lock()
                    .ok()
                    .and_then(|g| g.as_ref().map(|c| c.id()))
                    .unwrap_or_default(),
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
                            let _ = child.kill();
                            let _ = child.wait();
                        }
                    }
                }
            }
        });
}
