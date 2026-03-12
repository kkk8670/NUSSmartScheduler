import { BrowserRouter, Routes, Route } from "react-router-dom";
import NusSmartSchedulerStaticV2 from "./NusSmartSchedulerStaticV2.jsx";
import AgentMode from "./AgentPage.jsx";
import AuthPage from "./AuthPage.jsx";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<NusSmartSchedulerStaticV2 />} />
                <Route path="/agent" element={<AgentMode />} />
                <Route path="/auth" element={<AuthPage />} />
            </Routes>
        </BrowserRouter>
    );
}
