import React, { useState, useEffect, useRef } from "react";

import {
  Wand2,
  Calendar as CalendarIcon,
  Download,
  Map,
  Bus,
  Footprints,
  CloudRain,
  Clock,
  Flag,
  Settings,
  HelpCircle,
  TriangleAlert,
  MapPin,
  Route,
  Sparkles,
  Trash2,
  PlayCircle, ZoomIn, ZoomOut, Maximize2, X
} from "lucide-react";
import "./scheduler.css";

const API_BASE = "http://localhost:8000"; // ← 改成你的后端地址

export default function NUSSmartSchedulerStaticV2() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [sliders, setSliders] = useState({
    late: 10,
    travel: 1,
    walking: 0.4,
    studyLate: 5,
    gymGap: 60,
    gapPenalty: 2,
    sameBuilding: 2,
  });

  const [plans, setPlans] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [colW, setColW] = useState(12);     // 每个 5 分钟格子的像素宽度（8~28）
  const [laneH, setLaneH] = useState(76);   // 每一“车道”的最小高度
  const [showFull, setShowFull] = useState(false);


  // 顶部定义
  const fullRef = useRef(null);

  useEffect(() => {
    if (!showFull || !fullRef.current) return;
    // 容器宽度
    const width = fullRef.current.getBoundingClientRect().width;
    const cols = TOTAL_COLS; // 168
    const colWidth = Math.floor(width / cols);
    setColW(Math.max(4, colWidth)); // 列宽至少 4px，避免太细不可读
  }, [showFull]);




  const [commuteMode, setCommuteMode] = useState("auto");
  useEffect(() => {
       if (!timeline?.length) return;
       const spans = timeline.map(t => spanSlots(t.start, t.end));
       const minSpan = Math.max(1, Math.min(...spans));
       const minPx = 140; // 最短事件至少 140px
       const suggested = Math.min(28, Math.max(8, Math.ceil(minPx / minSpan)));
       if (suggested > colW) setColW(suggested);
     }, [timeline]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/schedule`);
        const data = await res.json();
        if (!cancelled) {
          if (Array.isArray(data?.plans)) setPlans(data.plans);
          if (Array.isArray(data?.timeline)) setTimeline(data.timeline);
        }
      } catch (e) {
        console.error("加载 Plan/Timeline 失败：", e);
      } finally {
        if (!cancelled) {
          setLoadingPlans(false);
          setLoadingTimeline(false); // ← 现在有定义了
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // 在组件函数顶部 useState 部分加上：
  const [planTimelines, setPlanTimelines] = useState([]); // array of timelines
  const [activePlan, setActivePlan] = useState(0);        // index of selected plan

  const DAY_START_MIN = 8 * 60;     // 08:00 -> 480
  const SLOT_MIN = 5;               // 5 分钟一个格
  const TOTAL_COLS = (22 - 8) * 60 / SLOT_MIN; // 14h * 60 / 5 = 168

  function hhmmToMinutes(hhmm) {
    const [hh, mm] = hhmm.split(":").map(Number);
    return hh * 60 + mm;
  }
  function hhmmToSlot(hhmm) {
    return Math.max(0, Math.floor((hhmmToMinutes(hhmm) - DAY_START_MIN) / SLOT_MIN));
  }
  function spanSlots(startHHMM, endHHMM) {
    const s = hhmmToSlot(startHHMM);
    const e = hhmmToSlot(endHHMM);
    return Math.max(1, e - s);
  }

  // —— Today’s Tasks：纯前端本地管理（不从后端拉取），只在 Generate 时一次性 POST —— //
  const [tasks, setTasks] = useState([]);   // 初始空
  const [taskError, setTaskError] = useState("");
  const cidRef = useRef(1);                 // 本地临时 id 计数器
  const [taskForm, setTaskForm] = useState({
    title: "",
    loc: "",
    type: "Study",
    earliest: "",
    latest: "",
    duration: "",
    fixed: false,
  });

  const [locations, setLocations] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/locations`);
        const data = await res.json();
        if (Array.isArray(data?.locations)) setLocations(data.locations);
      } catch (e) {
        console.error("加载地点失败", e);
      }
    })();
  }, []);

  // 本地新增（不发请求）
  const handleCreateTaskLocal = () => {
    setTaskError("");
    const { title, loc, type, earliest, latest, duration, fixed } = taskForm;

    if (!title.trim() || !loc || !type || !earliest || !latest || !duration) {
      setTaskError("请填写完整：Title / Location / Type / Earliest / Latest / Duration");
      return;
    }

    const durNum = Number(duration);
    if (Number.isNaN(durNum) || durNum <= 0) {
      setTaskError("Duration 必须为大于 0 的数字（单位：分钟）");
      return;
    }

    // === 新增校验：Earliest <= Latest ===
    if (earliest > latest) {
      setTaskError("Earliest start 必须早于或等于 Latest start");
      return;
    }

    const cid = `c${cidRef.current++}`;
    const newTask = { id: cid, title, loc, type, earliest, latest, duration: durNum, fixed };
    setTasks((prev) => [newTask, ...prev]);

    setShowAddModal(false);
    setTaskForm({
      title: "",
      loc: "",
      type: "Study",
      earliest: "",
      latest: "",
      duration: "",
      fixed: false,
    });
  };


  // 本地删除（不发请求）
  const handleDeleteTaskLocal = (id) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  // Generate：一次性把当前任务列表 POST 给后端
  const [generating, setGenerating] = useState(false);
  const handleGenerate = async () => {
    if (tasks.length === 0) {
      alert("No tasks to submit. Please add tasks first.");
      return;
    }
    setGenerating(true);
    try {
      const tasksPayload = tasks.map(t => ({
        id: t.id,
        title: t.title,
        location: t.loc,
        type: t.type,
        earliest: t.earliest,
        latest: t.latest,
        duration_min: Number(t.duration),
        fixed: !!t.fixed,
      }));

      const res = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tasks: tasksPayload, commuteMode }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (Array.isArray(data?.plans)) setPlans(data.plans);

      if (Array.isArray(data?.all_timelines)) {
        setPlanTimelines(data.all_timelines);   // 三套 timeline
        setActivePlan(0);                       // 默认选第一套
        setTimeline(data.all_timelines[0] || []);
      } else if (Array.isArray(data?.timeline)) {
        setPlanTimelines([data.timeline]);
        setActivePlan(0);
        setTimeline(data.timeline);
      }



      console.log("Response /api/generate:", data);
    } catch (e) {
      console.error("Generate request failed:", e);
      alert("Submit failed, please try again later.");
    } finally {
      setGenerating(false);
    }
  };



  return (
      <div className="app">
        {/* Header */}
        <header className="header">
          <div className="container header__inner">
            <div className="brand">
              <div className="brand__icon"><Wand2 size={18} /></div>
              <div className="brand__text">
                <h1 className="brand__title">NUS Smart Scheduler · Prototype v2</h1>
                <p className="brand__subtitle">One-click plan · Travel buffers · Real-time replan · What-if</p>
              </div>
            </div>
            <div className="header__actions">
              <a className="btn btn--primary btn--sm">
                <CalendarIcon size={16}/>
                <span>Export iCal</span>
              </a>
              <a className="btn btn--outline btn--sm">
                <Download size={16}/>
                <span>CSV</span>
              </a>
              <a href="/agent" className="btn btn--dark btn--sm">
                <Sparkles size={16}/>
                <span>Agent Mode</span>
              </a>
            </div>
          </div>
        </header>

        <main className="container layout">
          {/* Left column */}
          <div className="layout__left">
            <Section
                title="Today's Tasks"
                icon={<Flag className="icon-16" />}
                right={
                  <div className="row gap-2">
                    <button className="tag tag--dark" onClick={() => setShowAddModal(true)}>
                      Add
                    </button>
                    <button
                        className="btn btn--primary btn--sm"
                        onClick={handleGenerate}
                        disabled={generating}
                        title="提交当前任务到后端进行生成"
                    >
                      <PlayCircle size={16} />
                      <span>{generating ? "Generating…" : "Generate"}</span>
                    </button>
                  </div>
                }
            >
              {tasks.length === 0 ? (
                  <div className="text-sm text-muted">No tasks yet. Click “Add”.</div>
              ) : (
                  <div className="stack-2">
                    {tasks.map((t) => (
                        <TaskCard
                            key={t.id}
                            title={t.title}
                            loc={t.loc}
                            type={t.type}
                            earliest={t.earliest}
                            latest={t.latest}
                            duration={t.duration}
                            badge={t.fixed ? "Fixed" : undefined}
                            onDelete={() => handleDeleteTaskLocal(t.id)}
                        />

                    ))}
                  </div>
              )}
            </Section>

            <Section title="Commute Mode" icon={<Map className="icon-16" />}>
              <div className="row gap-2">
                <ModeButton
                    active={commuteMode === "walk"}
                    onClick={() => setCommuteMode("walk")}
                    icon={<Footprints size={16} />}
                >
                  Walk only
                </ModeButton>

                <ModeButton
                    active={commuteMode === "transit"}
                    onClick={() => setCommuteMode("transit")}
                    icon={<Bus size={16} />}
                >
                  Bus/MRT
                </ModeButton>

                <ModeButton
                    active={commuteMode === "auto"}
                    onClick={() => setCommuteMode("auto")}
                    icon={<><Footprints size={16} /><Bus size={16} /></>}
                >
                  Auto (both)
                </ModeButton>
              </div>

              {/* 这块保持原样（雨天减速的静态进度条） */}
              <div className="grid-6 gap-2 mt-4 align-center">
                <div className="col-span-3 text-muted row gap-2 align-center"><CloudRain size={16}/> Rain slowdown</div>
                <div className="col-span-2 w-full">
                  <div className="progress"><div className="progress__bar" style={{ width: "25%" }} /></div>
                </div>
                <div className="text-muted">25%</div>
              </div>
            </Section>



            <Section title="Soft Constraints (Weights)" icon={<Settings className="icon-16" />}>
              <SliderRow label="Late penalty / min" value={sliders.late} onChange={(v)=>setSliders({...sliders, late:v})} max={20} />
              <SliderRow label="Travel penalty / min" value={sliders.travel} onChange={(v)=>setSliders({...sliders, travel:v})} max={10} />
              <SliderRow label="Walking penalty / min" value={sliders.walking} onChange={(v)=>setSliders({...sliders, walking:v})} step={0.1} max={5} />
              <SliderRow label="Study >22:30 penalty / min" value={sliders.studyLate} onChange={(v)=>setSliders({...sliders, studyLate:v})} max={10} />
              <SliderRow label="Gym after meal min gap" value={sliders.gymGap} onChange={(v)=>setSliders({...sliders, gymGap:v})} max={120} />
              <SliderRow label="Gap shortfall penalty / min" value={sliders.gapPenalty} onChange={(v)=>setSliders({...sliders, gapPenalty:v})} max={10} />
              <SliderRow label="Same building bonus" value={sliders.sameBuilding} onChange={(v)=>setSliders({...sliders, sameBuilding:v})} max={10} />
            </Section>

          </div>

          {/* Right column */}
          <div className="layout__right">
            <Section title="Plan Selector" icon={<Clock className="icon-16" />}>
              {loadingPlans ? (
                  <div className="text-sm text-muted">Loading plans…</div>
              ) : (
                  <div className="grid-3 gap-3">
                    {plans.map((p, i) => (
                        <PlanCard
                            key={i}
                            title={p.title}
                            desc={p.desc}
                            meta={p.meta}
                            active={i === activePlan}   // 高亮当前选中
                            onClick={() => {
                              if (planTimelines[i]) {
                                setActivePlan(i);
                                setTimeline(planTimelines[i]); // 切换时间线
                              }
                            }}
                        />
                    ))}
                  </div>
              )}
            </Section>

            <Section
                title="Timeline"
                icon={<Route className="icon-16" />}
                right={
                  <div className="row gap-2">
                    <button className="tag" onClick={() => setColW(w => Math.max(8, w - 2))} title="缩小">
                      <ZoomOut size={14} />
                    </button>
                    <button className="tag" onClick={() => setColW(w => Math.min(28, w + 2))} title="放大">
                      <ZoomIn size={14} />
                    </button>
                    <button className="tag" onClick={() => setShowFull(true)} title="全屏查看">
                      <Maximize2 size={14} />
                    </button>
                  </div>
                }
            >
              <TimelineHours />

              <div
                  className="timeline-grid mt-3"
                  style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${TOTAL_COLS}, ${colW}px)`,          // ✅ 列宽=像素
                    gridAutoRows: `minmax(${laneH}px, auto)`,
                    rowGap: 10, columnGap: 6,
                    border: "1px dashed #e2e8f0",
                    padding: 6,
                    overflowX: "auto" ,
                    borderRadius: 12,

                  }}
              >
                {(timeline?.length ? timeline : [
                  { title: "DEMO very very long title shows clamp", loc: "ISS Inspire Theatre", start: "09:00", end: "10:30", color: "indigo" }
                ]).map((t, idx) => {
                  const colStart = hhmmToSlot(t.start) + 1;
                  const colSpan  = spanSlots(t.start, t.end);
                  const minutes  = colSpan * SLOT_MIN;

                  // ✅ 动态决定标题可占行数：短=1，中=2，长=3
                  const titleLines = minutes >= 90 ? 3 : minutes >= 45 ? 2 : 1;

                  return (
                      <div
                          key={idx}
                          className={"timelinebar timelinebar--" + (t.color || "indigo")}
                          style={{
                            gridColumn: `${colStart} / span ${colSpan}`,
                            gridRow: idx + 1,                        // 仍然一事一行
                            // 把可用标题行数传给 CSS（容器可变高时更好看）
                            ["--title-lines"]: titleLines,
                          }}
                      >
                        <span className="timelinebar__index">{idx + 1}</span>

                        {/* 标题：按行数动态裁剪 */}
                        <div className="timelinebar__title">{t.title || ""}</div>

                        <div className="row between align-center mt-1" style={{ minWidth: 0 }}>
                          <span className="pill pill--truncate">{t.loc}</span>
                          <div className="timelinebar__time text-sm text-muted">
                            {t.start} — {t.end}
                          </div>
                        </div>
                      </div>
                  );
                })}
              </div>
            </Section>



            {/*<Section title="Notes" icon={<TriangleAlert className="icon-16" />}>*/}
            {/*  <ul className="list">*/}
            {/*    <li>100% static prototype: visuals only, no logic or data fetching.</li>*/}
            {/*    <li>Numbers, times and locations are placeholders for UI review.</li>*/}
            {/*    <li>Export buttons are non-functional in this mock.</li>*/}
            {/*  </ul>*/}
            {/*</Section>*/}
          </div>
        </main>

        

        {/* Add Task Modal（本地新增，不发请求） */}
        {showFull && (
            <div className="modal-overlay">
              <div className="modal modal--xl">
                <div className="row between align-center">
                  <div className="fw-600">Timeline · Fullscreen</div>
                  <div className="row gap-2">
                    <button className="tag" onClick={() => setColW(w => Math.max(8, w - 2))}><ZoomOut size={14}/></button>
                    <button className="tag" onClick={() => setColW(w => Math.min(28, w + 2))}><ZoomIn size={14}/></button>
                    <button className="tag" onClick={() => setShowFull(false)} title="关闭"><X size={14}/></button>
                  </div>
                </div>

                <div className="timeline-fullbody mt-3" ref={fullRef}>
                  <TimelineHours/>
                  <div
                      className="timeline-grid"
                      style={{
                        display: "grid",
                        gridTemplateColumns: `repeat(${TOTAL_COLS}, ${colW}px)`,
                        gridAutoRows: `minmax(${laneH}px, auto)`,
                        rowGap: 12, columnGap: 8,
                        padding: 8,
                        overflow: "auto",
                        height: "100%"
                      }}
                  >
                    {timeline.map((t, idx) => {
                      const colStart = hhmmToSlot(t.start) + 1;
                      const colSpan = spanSlots(t.start, t.end);
                      return (
                          <div
                              key={idx}
                              className={"timelinebar timelinebar--" + (t.color || "indigo")}
                              style={{gridColumn: `${colStart} / span ${colSpan}`, gridRow: idx + 1}}
                          >
                            <span className="timelinebar__index">{idx + 1}</span>
                            <div className="timelinebar__title">{t.title || ""}</div>
                            <div className="row between align-center mt-1" style={{minWidth: 0}}>
                              <span className="pill pill--truncate">{t.loc}</span>
                              <div className="timelinebar__time text-sm text-muted">{t.start} — {t.end}</div>
                            </div>
                          </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
        )}

        {showAddModal && (
            <div className="modal-overlay">
              <div className="modal">
                <h3>Add Task</h3>

                <input
                    type="text"
                    placeholder="Task title"
                    className="input mt-2 w-full"
                    value={taskForm.title}
                    onChange={(e) => setTaskForm({...taskForm, title: e.target.value})}
                />
                <div className="select-wrapper mt-2">
                  <CustomSelect
                      options={locations}
                      value={taskForm.loc}
                      onChange={(val) => setTaskForm({...taskForm, loc: val})}
                  />
                </div>


                <CustomSelect
                    options={["Class", "Meal", "Study", "Gym", "Other"]}
                    value={taskForm.type}
                    onChange={(val) => setTaskForm({...taskForm, type: val})}
                />
                <div className="form-field">
                  <TimePicker
                      value={taskForm.earliest || ""}
                      onChange={(val) => setTaskForm({...taskForm, earliest: val})}
                      startHour={8}
                      endHour={22}
                      step={15}
                      placeholder="Earliest start"
                  />
                </div>

                <div className="form-field">
                  <TimePicker
                      value={taskForm.latest || ""}
                      onChange={(val) => setTaskForm({...taskForm, latest: val})}
                      startHour={8}
                      endHour={22}
                      step={15}
                      placeholder="Latest start"
                  />
                </div>

                <div className="form-field">
                  <input
                      type="number"
                      min="5"
                      step="5"
                      placeholder="Duration (min)"
                      className="input w-full"
                      value={taskForm.duration || ""}
                      onChange={(e) => setTaskForm({...taskForm, duration: e.target.value})}
                  />
                </div>

                <label className="row gap-2 mt-2 align-center text-sm text-muted">
                  <input
                      type="checkbox"
                      checked={taskForm.fixed}
                      onChange={(e) => setTaskForm({...taskForm, fixed: e.target.checked})}
                  />
                  Fixed
                </label>

                {taskError && <div className="text-sm" style={{color: "#b91c1c", marginTop: 8}}>{taskError}</div>}

                <div className="row gap-2 mt-3">
                  <button className="btn btn--primary" onClick={handleCreateTaskLocal}>Save</button>
                  <button className="btn btn--outline" onClick={() => setShowAddModal(false)}>Cancel</button>
                </div>
              </div>
            </div>
        )}
      </div>
  );
}

// ————— Components —————
function Section({title, icon, right, children}) {
  return (
      <div className="section">
        <div className="section__head">
          <div className="row gap-2 align-center text-700">
            {icon}
            <h3 className="section__title">{title}</h3>
          </div>
          {right}
        </div>
        {children}
      </div>
  );
}

function TimePicker({
                      value,
                      onChange,
                      startHour = 8,   // 起始小时
                      endHour = 22,    // 结束小时（含）
                      step = 15,       // 分钟步长：5/10/15/30 ...
                      placeholder = "请选择时间",
                    }) {
  const [open, setOpen] = React.useState(false);
  const boxRef = React.useRef(null);

  // 生成时间网格
  const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);
  const minutes = Array.from({ length: 60 / step }, (_, i) => i * step);
  const fmt = (h, m) => `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;

  // 点击外部关闭
  React.useEffect(() => {
    const onDocClick = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  return (
      <div className={`select-box ${open ? "open" : ""}`} ref={boxRef}>
        <div
            className="select-display"
            role="button"
            tabIndex={0}
            onClick={() => setOpen((v) => !v)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setOpen((v) => !v)}
        >
          {value || placeholder}
        </div>

        {open && (
            <div className="select-options" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
              {hours.map((h) =>
                  minutes.map((m) => {
                    const t = fmt(h, m);
                    const sel = value === t;
                    return (
                        <div
                            key={t}
                            className={`option${sel ? " selected" : ""}`}
                            onClick={() => { onChange(t); setOpen(false); }}
                        >
                          {t}
                        </div>
                    );
                  })
              )}
            </div>
        )}
      </div>
  );
}

function TaskCard({ title, loc, type, earliest, latest, duration, badge, onDelete }) {
  return (
      <div className="card card--soft">
        <div className="row between align-center">
          <div className="text-900 fw-500">{title}</div>
          <div className="row gap-2 align-center">
            {badge ? <span className="chip chip--indigo">{badge}</span> : null}
            {onDelete && (
                <button className="btn btn--outline btn--sm" onClick={onDelete} title="Delete">
                  <Trash2 size={14} />
                </button>
            )}
          </div>
        </div>

        <div className="row gap-2 mt-1 text-muted text-sm align-center">
          <MapPin size={14} /><span>{loc}</span><span>·</span><span className="badge">{type}</span>
        </div>

        <div className="row gap-2 mt-1 text-muted text-sm align-center">
          <Clock size={14} />
          <span>{earliest || "—"} — {latest || "—"} · {duration ? `${duration}min` : "—"}</span>
        </div>
      </div>
  );
}

function CustomSelect({ options, value, onChange }) {
  const [open, setOpen] = React.useState(false);

  return (
      <div className="select-box">
        <div
            className="select-display"
            onClick={() => setOpen(!open)}
        >
          {value || "Please select location"}
        </div>
        {open && (
            <ul className="select-options">
              {options.map((opt) => (
                  <li
                      key={opt}
                      className={`option ${value === opt ? "selected" : ""}`}
                      onClick={() => {
                        onChange(opt);
                        setOpen(false);
                      }}
                  >
                    {opt}
                  </li>
              ))}
            </ul>
        )}
      </div>
  );
}

function ModeButton({ active, icon, children, onClick }) {
  return (
      <span
          role="button"
          tabIndex={0}
          aria-pressed={!!active}
          onClick={onClick}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick?.(); }
          }}
          className={"modebtn" + (active ? " modebtn--active" : "") }
          style={{ userSelect: "none", cursor: "pointer"  }}
      >
      {icon}
        {children}
    </span>
  );
}


function SliderRow({ label, value, onChange, min=0, max=100, step=1 }) {
  return (
      <div className="grid-12 gap-2 align-center py-1">
        <div className="col-span-6 text-sm text-muted">{label}</div>
        <div className="col-span-4">
          <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => onChange(parseFloat(e.target.value))}
              className="slider w-full"
              style={{ "--value": (value / max) * 100 }}
          />
        </div>
        <div className="col-span-2 text-right text-sm text-muted">{value}</div>
      </div>
  );
}

function PlanCard({ title, desc, meta, active, onClick }) {
  return (
      <div
          className={"plancard" + (active ? " plancard--active" : "")}
          onClick={onClick}
          style={{ cursor: "pointer" }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onClick?.();
          }}
      >
        <div className="row between align-center">
          <div className="fw-600">{title}</div>
          <span className={"meta" + (active ? " meta--active" : "")}>{meta}</span>
        </div>
        <div className={"text-sm mt-1" + (active ? " text-200" : " text-muted")}>{desc}</div>
      </div>
  );
}



function TimelineHours() {
  const hours = [
    "08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00",
    "16:00","17:00","18:00","19:00","20:00","21:00","22:00"
  ];
  return (
      <div className="grid-15 gap-1 hours">
        {hours.map((h) => (
            <div key={h} className="hours__cell">{h}</div>
        ))}
      </div>
  );
}

function TimelineItem({ title, loc, start, end, travel, color }) {
  return (
      <div className={"timelineitem timelineitem--" + color}>
        <div className="row between align-center">
          <div className="fw-500 text-900">{title}</div>
          <span className="pill">{loc}</span>
        </div>
        <div className="text-sm text-muted mt-1">{start} – {end} · travel in {travel}</div>
      </div>
  );
}
function HeatRow({ label, value, max }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
      <div className="row gap-2 align-center">
        <div className="w-28 text-xs text-muted">{label}</div>
        <div className="progress progress--lg flex-1"><div className="progress__bar" style={{ width: pct + "%" }} /></div>
        <div className="w-10 text-right text-xs text-muted">{value}′</div>
      </div>
  );
}

function ChatBubble({ role, text }) {
  const isAssistant = role !== "user";
  return (
      <div className={"chatbubble" + (isAssistant ? " chatbubble--assistant" : " chatbubble--user") }>
        {text}
      </div>
  );
}
