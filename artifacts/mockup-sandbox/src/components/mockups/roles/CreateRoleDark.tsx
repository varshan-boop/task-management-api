import { useState } from "react";
import "./CreateRoleDark.css";

const swatches = ["#a3b3bf", "#8a9aff", "#e07a91", "#e6ab69", "#82bd91", "#56b9b7", "#c587df"];

export default function CreateRoleDark() {
  const [name, setName] = useState("new role");
  const [color, setColor] = useState(swatches[0]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [keyboardOpen, setKeyboardOpen] = useState(true);
  const [step, setStep] = useState(1);
  const [closed, setClosed] = useState(false);

  const append = (value: string) => setName((current) => `${current}${value}`);
  const pressKey = (key: string) => {
    if (key === "⌫") {
      setName((current) => current.slice(0, -1));
    } else if (key === "space") {
      append(" ");
    } else if (key === "done") {
      setKeyboardOpen(false);
    } else {
      append(key);
    }
  };

  return (
    <div className="role-dark">
      <div className="rd-status" aria-label="Phone status bar">
        <span>9:41</span>
        <div className="rd-status-icons">
          <svg width="18" height="15" viewBox="0 0 18 15" aria-hidden="true">
            <path d="M1 13V9.4h2.7V13M5.2 13V6.6h2.7V13M9.4 13V4h2.7v9M13.6 13V1h2.7v12" fill="currentColor" />
          </svg>
          <svg width="17" height="15" viewBox="0 0 17 15" aria-hidden="true">
            <path d="M1.2 5.2a10.5 10.5 0 0 1 14.6 0M3.7 7.8a6.9 6.9 0 0 1 9.6 0M6.3 10.4a3.3 3.3 0 0 1 4.4 0M8.5 13h.01" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
          <svg width="28" height="14" viewBox="0 0 28 14" aria-hidden="true">
            <rect x=".7" y="1" width="23" height="12" rx="3.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
            <rect x="2.8" y="3.1" width="18.5" height="7.8" rx="1.6" fill="currentColor" />
            <path d="M25 4.4v5.2a2.5 2.5 0 0 0 0-5.2Z" fill="currentColor" />
          </svg>
        </div>
      </div>

      {closed ? (
        <div className="rd-closed">
          <div>
            <div className="rd-closed-mark">
              <svg width="25" height="25" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 12.5 9.2 17 19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h2>Role draft saved</h2>
            <p>Your new role is waiting right where you left it.</p>
            <button className="rd-create" onClick={() => setClosed(false)}>Continue setup</button>
          </div>
        </div>
      ) : (
        <>
          <header className="rd-topbar">
            <button className="rd-icon-button" aria-label="Close role setup" onClick={() => setClosed(true)}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="m5 5 10 10M15 5 5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
            <div className="rd-step-label">Step {step} of 3</div>
            <span aria-hidden="true" />
          </header>

          {step === 1 ? (
            <>
              <main className="rd-main">
                <section className="rd-intro">
                  <p className="rd-eyebrow">Community roles</p>
                  <h1>Create a new role</h1>
                  <p>Give this role a unique name and color. You can always change this later.</p>
                </section>

                <label className="rd-field-label" htmlFor="role-name">ROLE NAME</label>
                <input
                  id="role-name"
                  className="rd-name-input"
                  value={name}
                  onFocus={() => setKeyboardOpen(true)}
                  onChange={(event) => setName(event.currentTarget.value)}
                  maxLength={32}
                />
                <p className="rd-field-hint">e.g. coach, moderator, subscriber, pet club</p>

                <button className="rd-color-row" onClick={() => {
                  setPaletteOpen((open) => !open);
                  if (!paletteOpen) setKeyboardOpen(false);
                }} aria-expanded={paletteOpen}>
                  <span className="rd-color-title">Role color</span>
                  <span className="rd-color-sample" style={{ backgroundColor: color }} />
                  <span className="rd-hex">{color}</span>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path d="m6 3.5 4.5 4.5L6 12.5" stroke="#9da8b7" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {paletteOpen ? (
                  <div className="rd-palette">
                    <p className="rd-palette-title">Choose a color</p>
                    <div className="rd-swatches">
                      {swatches.map((swatch) => (
                        <button
                          key={swatch}
                          className={`rd-swatch${color === swatch ? " is-selected" : ""}`}
                          style={{ backgroundColor: swatch }}
                          aria-label={`Choose ${swatch}`}
                          aria-pressed={color === swatch}
                          onClick={() => setColor(swatch)}
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="rd-color-note">Members show the color of their highest role in the member list.</p>
                )}
              </main>

              <div className="rd-create-wrap">
                <button className="rd-create" disabled={!name.trim()} onClick={() => {
                  setStep(2);
                  setKeyboardOpen(false);
                  setPaletteOpen(false);
                }}>Create role</button>
              </div>

              {keyboardOpen && !paletteOpen ? (
                <div className="rd-keyboard" aria-label="On-screen keyboard">
                  <div className="rd-keyboard-toolbar"><span>◉</span><span>•••</span><span>⌄</span></div>
                  {["qwertyuiop", "asdfghjkl"].map((row, index) => (
                    <div className={`rd-keys${index === 1 ? " rd-keys-indented" : ""}`} key={row}>
                      {Array.from(row).map((character) => (
                        <button className="rd-key" key={character} onClick={() => pressKey(character)}>{character}</button>
                      ))}
                    </div>
                  ))}
                  <div className="rd-keys">
                    <button className="rd-key rd-key-special" onClick={() => pressKey(" ")}>⇧</button>
                    {"zxcvbnm".split("").map((character) => (
                      <button className="rd-key" key={character} onClick={() => pressKey(character)}>{character}</button>
                    ))}
                    <button className="rd-key rd-key-special" onClick={() => pressKey("⌫")}>⌫</button>
                  </div>
                  <div className="rd-keys">
                    <button className="rd-key rd-key-special" onClick={() => pressKey(" ")}>123</button>
                    <button className="rd-key" onClick={() => pressKey(",")}>,</button>
                    <button className="rd-key" style={{ flex: 4 }} onClick={() => pressKey("space")}>space</button>
                    <button className="rd-key" onClick={() => pressKey(".")}>.</button>
                    <button className="rd-key rd-key-accent" onClick={() => pressKey("done")}>done</button>
                  </div>
                  <div className="rd-keyboard-bottom">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
                      <path d="M8.5 14.3c.8 1 2 1.5 3.5 1.5s2.7-.5 3.5-1.5M8.8 9.7h.01M15.2 9.7h.01" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    </svg>
                    <svg width="18" height="23" viewBox="0 0 18 23" fill="none" aria-hidden="true">
                      <rect x="6" y="1" width="6" height="13" rx="3" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M2.5 10.5a6.5 6.5 0 0 0 13 0M9 17v4M6 21h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div className="rd-home-indicator" />
                </div>
              ) : <div className="rd-hidden-keyboard"><div className="rd-home-indicator" /></div>}
            </>
          ) : step === 2 ? (
            <>
              <main className="rd-main rd-step-two">
                <section className="rd-intro">
                  <p className="rd-eyebrow">One more thing</p>
                  <h1>Set role permissions</h1>
                  <p>Choose what members with this role can do. You can fine-tune everything later.</p>
                </section>
                <div className="rd-summary-card">
                  <p className="rd-summary-kicker">New role preview</p>
                  <div className="rd-role-preview">
                    <span className="rd-role-preview-dot" style={{ backgroundColor: color }} />
                    <span className="rd-role-preview-name">{name}</span>
                  </div>
                </div>
                <div className="rd-permission-list">
                  {["View channels", "Send messages", "Manage threads"].map((permission, index) => (
                    <label className="rd-permission" key={permission}>
                      <input type="checkbox" defaultChecked={index < 2} />
                      <span>{permission}</span>
                    </label>
                  ))}
                </div>
              </main>
              <div className="rd-create-wrap">
                <button className="rd-create" onClick={() => setStep(3)}>Review role</button>
                <button className="rd-icon-button" style={{ width: "100%", marginTop: 3, fontSize: 12 }} onClick={() => setStep(1)}>Back to role details</button>
              </div>
              <div className="rd-hidden-keyboard"><div className="rd-home-indicator" /></div>
            </>
          ) : (
            <>
              <main className="rd-main rd-step-two">
                <section className="rd-intro">
                  <p className="rd-eyebrow">Ready when you are</p>
                  <h1>Your role is set</h1>
                  <p>Everything looks good. This role will be available to your community as soon as you finish.</p>
                </section>
                <div className="rd-summary-card">
                  <p className="rd-summary-kicker">Role summary</p>
                  <div className="rd-role-preview">
                    <span className="rd-role-preview-dot" style={{ backgroundColor: color }} />
                    <span className="rd-role-preview-name">{name}</span>
                  </div>
                </div>
                <p className="rd-color-note">Your role color and permissions can be updated any time in community settings.</p>
              </main>
              <div className="rd-create-wrap">
                <button className="rd-create" onClick={() => setClosed(true)}>Finish setup</button>
                <button className="rd-icon-button" style={{ width: "100%", marginTop: 3, fontSize: 12 }} onClick={() => setStep(2)}>Back to permissions</button>
              </div>
              <div className="rd-hidden-keyboard"><div className="rd-home-indicator" /></div>
            </>
          )}
        </>
      )}
    </div>
  );
}