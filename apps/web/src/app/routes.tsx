import { Navigate, Outlet, Route, Routes, useLocation } from "react-router";
import { useSession } from "../lib/auth";
import { AppShell } from "../components/AppShell";
import { ChatPage } from "../features/chat/ChatPage";
import { SignInPage, SignUpPage } from "../features/auth/AuthPages";
import { NewProjectPage } from "../features/projects/NewProjectPage";
import { ProjectPage } from "../features/projects/ProjectPage";
import { ComingSoon } from "../components/ComingSoon";
import { ArchivePage } from "../features/archive/ArchivePage";
import { FamilyPage, PersonPage } from "../features/family/FamilyPages";
import { LifelinePage } from "../features/lifeline/LifelinePage";
import { FamilyGalleryPage } from "../features/family/Gallery";
import { LifeReportPage } from "../features/family/LifeReport";
import { ExplainPage } from "../features/explain/ExplainRecord";
import { LineagePage, LineagesPage } from "../features/lineages/LineagesPage";
import { InterviewPage } from "../features/interview/InterviewPage";
import { MapPage } from "../features/map/MapPage";
import { SearchPage } from "../features/search/SearchPage";

function RequireAuth() {
  const session = useSession();
  const location = useLocation();
  if (session.isPending) {
    return <p className="p-8 text-muted">Loading…</p>;
  }
  if (session.isError) {
    return <p className="p-8 text-warning">Couldn't reach ArchiveHub. Is the API running?</p>;
  }
  if (!session.data) {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/signin" element={<SignInPage />} />
      <Route path="/signup" element={<SignUpPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat/:chatId?" element={<ChatPage />} />
          <Route path="projects/new" element={<NewProjectPage />} />
          <Route path="projects/:projectId" element={<ProjectPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="forums" element={<ComingSoon title="Forums" pkg="WP8" />} />
          <Route path="archive" element={<ArchivePage />} />
          <Route path="projects/:projectId/people" element={<FamilyPage />} />
          <Route path="projects/:projectId/lifeline" element={<LifelinePage />} />
          <Route path="projects/:projectId/gallery" element={<FamilyGalleryPage />} />
          <Route path="projects/:projectId/people/:personId/report" element={<LifeReportPage />} />
          <Route path="explain" element={<ExplainPage />} />
          <Route path="lineages" element={<LineagesPage />} />
          <Route path="lineages/:type/:id" element={<LineagePage />} />
          <Route path="projects/:projectId/people/:personId" element={<PersonPage />} />
          <Route path="interviews/:interviewId" element={<InterviewPage />} />
          <Route path="homepage" element={<ComingSoon title="Homepage" pkg="WP7" />} />
          <Route path="profile" element={<ComingSoon title="Profile" pkg="WP8" />} />
          <Route path="settings" element={<ComingSoon title="Settings" pkg="a later package" />} />
          <Route path="*" element={<ComingSoon title="Page not found" />} />
        </Route>
      </Route>
    </Routes>
  );
}
