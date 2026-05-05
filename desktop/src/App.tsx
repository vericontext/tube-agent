import { Routes, Route, Navigate } from "react-router-dom";
import { SidecarGate } from "@/components/SidecarGate";
import { AppShell } from "@/components/AppShell";
import { ChannelsPage } from "@/pages/ChannelsPage";
import { ChannelDetailPage } from "@/pages/ChannelDetailPage";
import { JobPage } from "@/pages/JobPage";
import { SearchPage } from "@/pages/SearchPage";
import { VideoDetailPage } from "@/pages/VideoDetailPage";

export default function App() {
  return (
    <SidecarGate>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<ChannelsPage />} />
          <Route path="/channels/:handle" element={<ChannelDetailPage />} />
          <Route path="/channels/:handle/videos/:videoId" element={<VideoDetailPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </SidecarGate>
  );
}
