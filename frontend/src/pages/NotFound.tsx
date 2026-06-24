import { Link } from "react-router-dom";
import { Logo } from "@/components/Logo";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <Logo size={26} />
      <h1 className="font-display text-3xl font-semibold text-ink">404</h1>
      <p className="max-w-sm text-sm text-muted">
        This page doesn't exist — or the short link you followed has been removed.
      </p>
      <Link to="/dashboard" className="btn-secondary mt-2">
        Go to dashboard
      </Link>
    </div>
  );
}
