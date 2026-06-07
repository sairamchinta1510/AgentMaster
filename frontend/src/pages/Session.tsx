import { useParams, Navigate } from "react-router-dom";

// v1 Session page deprecated — redirect to DesignPage
export function Session() {
  const { sessionId } = useParams<{ sessionId: string }>();
  return <Navigate to={sessionId ? `/design/${sessionId}` : "/"} replace />;
}
