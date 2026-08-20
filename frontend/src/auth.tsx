import { type FormEvent, useState } from "react";
import { api, messageOf } from "./api";
import { type AuthForm, passwordError, usernameError, validate } from "./auth-validation";
import { useToast } from "./toast";

const inputClass = "rounded border border-gray-300 bg-white px-3 py-2.5 text-gray-900";
const buttonClass = "rounded bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white";
const errorClass = "text-xs text-red-600";

export function LoginScreen({ notice, onSuccess, onRegister }: { notice?: string; onSuccess: () => void; onRegister: () => void }) {
  const [form, setForm] = useState<AuthForm>({ username: "", password: "" });
  const [errors, setErrors] = useState<{ username: string; password: string }>({ username: "", password: "" });
  const showToast = useToast();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const checked = validate(form);
    setErrors(checked.errors);
    if (!checked.valid) return;
    try {
      await api.login(form.username, form.password);
      onSuccess();
    } catch (error) {
      showToast(messageOf(error));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-sm flex-col gap-6 px-6 py-16">
      <header className="flex flex-col gap-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">Game Leaders</span>
        <h1 className="text-3xl font-bold">Log in</h1>
        <p className="text-sm text-gray-600">Pick up where your table left off.</p>
        {notice && <p className="rounded bg-green-50 px-3 py-2 text-sm font-semibold text-green-700">{notice}</p>}
      </header>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Username
          <input className={inputClass} value={form.username} onChange={(e) => { setForm((f) => ({ ...f, username: e.target.value })); setErrors((prev) => ({ ...prev, username: usernameError(e.target.value) })); }} autoFocus />
          {errors.username && <span className={errorClass}>{errors.username}</span>}
        </label>
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Password
          <input className={inputClass} type="password" value={form.password} onChange={(e) => { setForm((f) => ({ ...f, password: e.target.value })); setErrors((prev) => ({ ...prev, password: passwordError(e.target.value) })); }} />
          {errors.password && <span className={errorClass}>{errors.password}</span>}
        </label>
        <button className={buttonClass} type="submit">Log in</button>
      </form>
      <p className="text-center text-sm text-gray-600">
        No account? <button className="font-semibold text-blue-600" onClick={onRegister}>Register</button>
      </p>
    </main>
  );
}

export function RegisterScreen({ onSuccess, onLogin }: { onSuccess: () => void; onLogin: () => void }) {
  const [form, setForm] = useState<AuthForm>({ username: "", password: "" });
  const [errors, setErrors] = useState<{ username: string; password: string }>({ username: "", password: "" });
  const showToast = useToast();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const checked = validate(form);
    setErrors(checked.errors);
    if (!checked.valid) return;
    try {
      await api.register(form.username, form.password);
      onSuccess();
    } catch (error) {
      showToast(messageOf(error));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-sm flex-col gap-6 px-6 py-16">
      <header className="flex flex-col gap-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">Game Leaders</span>
        <h1 className="text-3xl font-bold">Register</h1>
        <p className="text-sm text-gray-600">Username and password. No email needed.</p>
      </header>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Username
          <input className={inputClass} value={form.username} onChange={(e) => { setForm((f) => ({ ...f, username: e.target.value })); setErrors((prev) => ({ ...prev, username: usernameError(e.target.value) })); }} autoFocus />
          {errors.username && <span className={errorClass}>{errors.username}</span>}
        </label>
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Password
          <input className={inputClass} type="password" value={form.password} onChange={(e) => { setForm((f) => ({ ...f, password: e.target.value })); setErrors((prev) => ({ ...prev, password: passwordError(e.target.value) })); }} />
          {errors.password && <span className={errorClass}>{errors.password}</span>}
        </label>
        <button className={buttonClass} type="submit">Create account</button>
      </form>
      <p className="text-center text-sm text-gray-600">
        Already registered? <button className="font-semibold text-blue-600" onClick={onLogin}>Log in</button>
      </p>
    </main>
  );
}
