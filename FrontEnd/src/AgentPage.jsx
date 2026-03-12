import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./agent.css";

export default function AgentChatLite() {
    const [msgs, setMsgs] = useState([
        { role: "assistant", text: "Hi! Tell me your day and I'll plan it. When a plan is ready, you'll see an Open Timeline button." }
    ]);
    const [text, setText] = useState("");
    const [plan, setPlan] = useState([]);
    const [showBanner, setShowBanner] = useState(false);
    const [drawer, setDrawer] = useState(false);
    const chatRef = useRef(null);
    const toMin = (hhmm) => {
        const [h, m] = hhmm.split(":").map(Number);
        return h * 60 + m;
    };

    const items = plan.length ? plan : demoPlan;
    const defaultStart = 8 * 60;
    const earliestMin = items.length ? Math.min(...items.map(it => toMin(it.start))) : defaultStart;

    const START = Math.max(0, Math.floor(earliestMin / 60) * 60 );
    const END   = 22 * 60;
    const SLOT  = 5;
    const totalCols = Math.max(1, Math.floor((END - START) / SLOT));

    const toCol = (hhmm) => Math.max(0, Math.floor((toMin(hhmm) - START) / SLOT)) + 1;
    const spanCols = (a, b) => Math.max(1, Math.floor((toMin(b) - toMin(a)) / SLOT));

    const push = (m) => {
        setMsgs((p) => [...p, m]);
        requestAnimationFrame(() =>
            chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" })
        );
    };

    // Translate raw ReAct steps into user-friendly messages
    function translateStep(step) {
        if (!step || !step.type) return null;

        const raw = (step.content || "").toString().trim();
        const tool = step.tool || "";
        let label = "";
        let text = "";
        let color = ""; // used for CSS class

        // Thought → Understanding
        if (step.type === "thought") {
            label = "Understanding";
            color = "blue";
            text = raw
                ? `Let me think about this: ${raw}`
                : "Let me analyze your request.";
            return { label, text, color };
        }

        // Action → based on tool
        if (step.type === "action") {
            if (tool === "memory_search_tool") {
                label = "Preference";
                color = "green";
                text = "Checking your past preferences...";
                return { label, text, color };
            }
            if (tool === "knowledge_search_tool") {
                label = "Information";
                color = "purple";
                text = "Looking up relevant information...";
                return { label, text, color };
            }
            if (tool === "schedule_suggest_tool") {
                label = "Planning";
                color = "orange";
                text = "Planning the best schedule...";
                return { label, text, color };
            }
            label = "Action";
            color = "gray";
            text = "Processing...";
            return { label, text, color };
        }

        if (step.type === "observation") {
            label = "Result";
            color = "gray";
            text = raw ? `I found: ${raw}` : "Got the result.";
            return { label, text, color };
        }

        return null;
    }


    // async function onSend() {
    //     const t = text.trim();
    //     if (!t) return;
    //
    //     push({ role: "user", text: t });
    //     setText("");
    //
    //     // 1) 读取 token
    //     const token = localStorage.getItem("auth.token");
    //
    //     // 2) 组装请求头（有 token 才加 Authorization）
    //     const headers = {
    //         "Content-Type": "application/json",
    //         ...(token ? { Authorization: `Bearer ${token}` } : {}),
    //     };
    //
    //     try {
    //         const res = await fetch("http://localhost:8000/agent/chat", {
    //             method: "POST",
    //             headers,
    //             body: JSON.stringify({ prompt: t }),
    //         });
    //         console.log(token)
    //         if (res.status === 401) {
    //             push({
    //                 role: "assistant",
    //                 text: "Please log in before chat, redirecting to log in page.",
    //             });
    //             setTimeout(() => {
    //                 window.location.href = "/auth?redirect=/agent";
    //             }, 1200);
    //             return;
    //         }
    //
    //         // 4) 其他错误
    //         if (!res.ok) {
    //             const errText = await res.text().catch(() => "");
    //             push({
    //                 role: "assistant",
    //                 text: `Service is not available（${res.status}）。${errText || ""}`,
    //             });
    //             return;
    //         }
    //
    //         // 5) 正常处理
    //         const data = await res.json();
    //         push({ role: "assistant", text: data.reply });
    //         if (Array.isArray(data.plan) && data.plan.length) {
    //             setPlan(data.plan);
    //             setShowBanner(true);
    //         }
    //     } catch (e) {
    //         push({ role: "assistant", text: "Network Error." });
    //     }
    // }
    const formatTime = (t) => {
        if (typeof t === "string" && t.includes(":")) {
            const parts = t.split(":");
            const h = parts[0].padStart(2, "0");
            const m = parts[1].padStart(2, "0");
            return `${h}:${m}`;
        }
        return "00:00";
    };



    async function onSend() {
        const t = text.trim();
        if (!t) return;

        push({ role: "user", text: t });
        setText("");

        const token = localStorage.getItem("auth.token");
        const headers = {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };

        try {
            const res = await fetch("http://localhost:8000/api/agent/chat/react", {
                method: "POST",
                headers,
                body: JSON.stringify({ prompt: t }),
            });

            if (res.status === 401) {
                push({ role: "assistant", text: "Please log in before chat, redirecting to log in page." });
                setTimeout(() => { window.location.href = "/auth?redirect=/agent"; }, 1200);
                return;
            }
            if (!res.ok) {
                const errText = await res.text().catch(() => "");
                push({ role: "assistant", text: `Service is not available (${res.status}). ${errText || ""}` });
                return;
            }

            const data = await res.json(); // { steps: [...], final: {...} }
            console.log("REACT RESPONSE:", data);


            // 逐条渲染中间过程（纯文本、无表情）
            if (Array.isArray(data.steps)) {
                for (const step of data.steps) {
                    const info = translateStep(step); // <-- NEW: use our translation
                    if (!info) continue;

                    const bubbleText = `[${info.label}] ${info.text}`;
                    push({ role: "assistant", text: bubbleText, color: info.color });

                    // Optional delay for a natural feel
                    await new Promise(r => setTimeout(r, 80));
                }

            }

            const final = data.final || {};
            const finalReply = (final.reply ?? "").toString() || "Done.";
            push({ role: "assistant", text: `[Final] ${finalReply}`, color: "blue" });


            if (Array.isArray(final.plan) && final.plan.length) {
                const normalized = final.plan.map(it => {
                    const start = it.start || it.earliest || "00:00";
                    const end = it.end || it.latest || "00:00";
                    return {
                        title: it.title || "Untitled",
                        loc: it.location || "",
                        start: formatTime(start),
                        end: formatTime(end),
                        color: it.color || "indigo"
                    };
                });

                setPlan(normalized);
                setShowBanner(true);
            }
        } catch (e) {
            console.error(e);
            push({ role: "assistant", text: "Network Error." });
        }
    }


    return (
        <div className="am2-root">
            {/* Header */}
            <header className="am2-header">
                <div className="am2-header__inner">
                    <div className="am2-brand">
                        <div className="am2-brand__icon">🤖</div>
                        <div>
                            <h1 className="am2-brand__title">Agent Mode</h1>
                            <div className="am2-brand__subtitle">Chat only · open timeline when ready</div>
                        </div>
                    </div>
                    <Link className="am2-btn" to="/auth">Login / Register</Link>
                    <button className="am2-btn" onClick={() => window.history.back()}>⬅ Back</button>
                </div>
            </header>

            {/* Main (centered single column) */}
            <main className="am2-main">
                <section className="am2-column">
                    <div className="am2-card">
                        <div className="am2-card__head">
                            <h2 className="am2-card__title">Conversation</h2>
                        </div>

                        <div ref={chatRef} className="am2-chat">
                            {msgs.map((m, i) => {
                                const bubbleClass = m.role === "assistant"
                                    ? `am2-bubble am2-bubble--assistant ${m.color ? "step-" + m.color : ""}`
                                    : "am2-bubble am2-bubble--user";

                                return (
                                    <div key={i} className={bubbleClass}>
                                        <div className="am2-bubble__meta">{m.role}</div>
                                        <div>{m.text}</div>
                                    </div>
                                );
                            })}


                        </div>

                        <div className="am2-composer">
              <textarea
                  className="am2-input"
                  rows={3}
                  placeholder="After class, go to USC for a 1-hour workout, then spend another 1 hour on problem-solving, and return to PGP before 9:30 PM."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onSend(); }}
              />
                            <div className="am2-row between">
                                <div className="am2-hint">Send: Ctrl/⌘ + Enter</div>
                                <button className="am2-btn am2-btn--primary" onClick={onSend}>Send</button>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* Bottom banner */}
            {showBanner && (
                <div className="am2-banner">
                    <div className="am2-banner__inner am2-card">
                        <div className="am2-row between center">
                            <div className="am2-text-sm am2-muted">A timeline has been generated for this chat.</div>
                            <div className="am2-row gap-2">
                                <button className="am2-btn" onClick={() => setShowBanner(false)}>Dismiss</button>
                                <button className="am2-btn am2-btn--primary" onClick={() => { setDrawer(true); setShowBanner(false); }}>Open Timeline</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Right drawer */}
            {drawer && (
                <div className="am2-overlay" onClick={() => setDrawer(false)}>
                    <aside className="am2-drawer" onClick={(e) => e.stopPropagation()}>
                        <div className="am2-row between center am2-drawer__head">
                            <div className="am2-fw-600">Timeline · Preview</div>
                            <button className="am2-btn" onClick={() => setDrawer(false)}>Close</button>
                        </div>



                        {/* grid */}
                        <div className="am2-grid"
                             style={{ gridTemplateColumns: `repeat(${totalCols}, var(--am2-colw))` }}>
                            {(plan.length ? plan : demoPlan).map((it, idx) => {
                                const colStart = toCol(it.start);
                                const colSpan = spanCols(it.start, it.end);
                                return (
                                    <div
                                        key={idx}
                                        className={`am2-item am2-item--${it.color || "indigo"}`}
                                        style={{ gridColumn: `${colStart} / span ${colSpan}`, gridRow: idx + 1 }}
                                        title={`${it.title} · ${it.start}-${it.end}${it.loc ? " @ " + it.loc : ""}`}
                                    >
                                        <div className="am2-item__title">{it.title}</div>
                                        <div className="am2-row gap-2 am2-mt-1">
                                            {it.loc && <span className="am2-pill am2-pill--truncate">@ {it.loc}</span>}
                                            <span className="am2-pill">{it.start}–{it.end}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
}

// ---- demo data & mock ----
const demoPlan = [
    { title: "Lecture",  loc: "AS6",  start: "14:00", end: "16:00", color: "indigo" },
    { title: "Meeting",  loc: "SR-2", start: "17:30", end: "18:30", color: "rose"   },
    { title: "Gym",      loc: "USC",  start: "19:00", end: "20:00", color: "emerald"},
];

