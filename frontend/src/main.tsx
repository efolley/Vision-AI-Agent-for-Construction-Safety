import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type User = { name: string; email: string };

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = email.trim();
    if (normalized) setUser({ email: normalized, name: normalized.split("@")[0] });
  }

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    if (selected?.type.startsWith("image/")) setFile(selected);
  }

  if (!user) return <main className="auth"><section className="card"><p className="eyebrow">VISION SAFETY AI</p><h1>Make jobsite safety visible.</h1><p>Sign in to start an inspection.</p><form onSubmit={signIn}><label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" /></label><button type="submit">Continue</button></form><small>Demo sign-in only. Production OIDC is pending.</small></section></main>;

  return <main className="app"><header><div><p className="eyebrow">VISION SAFETY AI</p><h1>Safety dashboard</h1></div><div className="user">{user.email}<button onClick={() => { setUser(null); setFile(null); }}>Sign out</button></div></header><section className="hero"><p className="eyebrow">NEW INSPECTION</p><h2>Upload a jobsite image</h2><p>We will validate it and create an inspection job.</p><label className="dropzone"><input type="file" accept="image/png,image/jpeg,image/webp" onChange={selectFile} /><span>{file ? file.name : "Choose an image"}</span><small>PNG, JPEG, or WebP · max 10 MB</small></label></section>{file && <section className="result"><img src={preview ?? ""} alt="Selected jobsite" /><div><span className="badge">WORK IN PROGRESS</span><h2>Inspection pipeline is being connected</h2><p>Your image is ready. Phase 1 provides the API foundation; the browser-to-gateway upload integration will be enabled next.</p><dl><div><dt>File</dt><dd>{file.name}</dd></div><div><dt>Size</dt><dd>{Math.ceil(file.size / 1024)} KB</dd></div><div><dt>Status</dt><dd>Awaiting upload integration</dd></div></dl></div></section>}</main>;
}
createRoot(document.getElementById("root")!).render(<App />);
