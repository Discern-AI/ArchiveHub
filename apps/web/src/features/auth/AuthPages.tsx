import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { signIn, signUp, useRefreshSession, useSession } from "../../lib/auth";

function AuthForm({ mode }: { mode: "signin" | "signup" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const session = useSession();
  const refresh = useRefreshSession();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/chat";

  if (session.data) return <Navigate to={from} replace />;

  const isSignup = mode === "signup";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await (isSignup ? signUp : signIn)(email, password);
      await refresh();
      navigate(from, { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-page px-4 py-10">
      <form
        onSubmit={submit}
        className="flex w-full max-w-[400px] flex-col gap-4 rounded-xl border border-line bg-surface p-6"
      >
        <div className="font-serif text-[28px] font-semibold">ArchiveHub</div>
        <h1 className="m-0 text-xl font-semibold">
          {isSignup ? "Create your account" : "Sign in"}
        </h1>
        <label className="flex flex-col gap-1 font-medium">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="min-h-11 rounded-lg border border-control px-3 font-normal"
          />
        </label>
        <label className="flex flex-col gap-1 font-medium">
          Password
          <input
            type="password"
            autoComplete={isSignup ? "new-password" : "current-password"}
            required
            minLength={isSignup ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="min-h-11 rounded-lg border border-control px-3 font-normal"
          />
        </label>
        {error && (
          <p role="alert" className="m-0 font-medium text-warning">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="min-h-11 cursor-pointer rounded-lg bg-accent font-semibold text-white disabled:opacity-60"
        >
          {busy ? "Please wait…" : isSignup ? "Create account" : "Sign in"}
        </button>
        <p className="m-0 text-sm text-muted">
          {isSignup ? (
            <>
              Already have an account? <Link to="/signin">Sign in</Link>
            </>
          ) : (
            <>
              New here? <Link to="/signup">Create an account</Link>
            </>
          )}
        </p>
        {isSignup && (
          <p className="m-0 text-sm text-muted">
            Everything you add is private unless you choose to publish it.
          </p>
        )}
      </form>
    </div>
  );
}

export const SignInPage = () => <AuthForm mode="signin" />;
export const SignUpPage = () => <AuthForm mode="signup" />;
