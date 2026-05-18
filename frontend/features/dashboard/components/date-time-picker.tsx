"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

// ─── helpers ────────────────────────────────────────────────────────────────

function parseDt(iso: string) {
  const [datePart, timePart = "00:00"] = iso.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.slice(0, 5).split(":").map(Number);
  return { year, month: month - 1, day, hour: hour ?? 0, minute: minute ?? 0 };
}

function fmtDt(year: number, month: number, day: number, hour: number, minute: number) {
  return `${year}-${p2(month + 1)}-${p2(day)}T${p2(hour)}:${p2(minute)}`;
}

function p2(n: number) {
  return String(n).padStart(2, "0");
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAY_ABBR = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

// ─── component ──────────────────────────────────────────────────────────────

export function DateTimePicker({
  value,
  onChange,
  minIso,
  maxIso,
  effectiveMinIso,
  disabled,
  label,
  required,
}: {
  value: string | null;
  onChange: (v: string | null) => void;
  minIso: string;
  maxIso: string;
  effectiveMinIso?: string | null;
  disabled?: boolean;
  label: string;
  required?: boolean;
}) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [popupStyle, setPopupStyle] = useState<React.CSSProperties>({});

  const minDt = parseDt(minIso);
  const maxDt = parseDt(maxIso);

  const effMin = (() => {
    if (!effectiveMinIso) return minDt;
    const e = parseDt(effectiveMinIso);
    return fmtDt(e.year, e.month, e.day, e.hour, e.minute) >=
      fmtDt(minDt.year, minDt.month, minDt.day, minDt.hour, minDt.minute)
      ? e
      : minDt;
  })();

  const initDt = value ? parseDt(value) : effMin;
  const [viewYear, setViewYear] = useState(initDt.year);
  const [viewMonth, setViewMonth] = useState(initDt.month);
  const [selYear, setSelYear] = useState<number | null>(value ? parseDt(value).year : null);
  const [selMonth, setSelMonth] = useState<number | null>(value ? parseDt(value).month : null);
  const [selDay, setSelDay] = useState<number | null>(value ? parseDt(value).day : null);
  const [selHour, setSelHour] = useState<number>(initDt.hour);
  const [selMinute, setSelMinute] = useState<number>(
    initDt.minute % 30 === 0 ? initDt.minute : 0,
  );

  // Sync selection state from committed value on every open
  useEffect(() => {
    if (!open) return;
    if (value) {
      const d = parseDt(value);
      setViewYear(d.year);
      setViewMonth(d.month);
      setSelYear(d.year);
      setSelMonth(d.month);
      setSelDay(d.day);
      setSelHour(d.hour);
      setSelMinute(d.minute);
    } else {
      setViewYear(effMin.year);
      setViewMonth(effMin.month);
      setSelYear(null);
      setSelMonth(null);
      setSelDay(null);
      setSelHour(effMin.hour);
      setSelMinute(effMin.minute % 30 === 0 ? effMin.minute : 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Position popup fixed below (or above) the trigger
  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const popupW = Math.max(rect.width, 248);
    const popupH = 420;
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow >= popupH ? rect.bottom + 6 : rect.top - popupH - 6;
    const left = Math.min(rect.left, window.innerWidth - popupW - 8);
    setPopupStyle({ position: "fixed", top, left, width: popupW, zIndex: 9999 });
  }, [open]);

  // Close on outside click or scroll
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (
        triggerRef.current?.contains(e.target as Node) ||
        popupRef.current?.contains(e.target as Node)
      )
        return;
      setOpen(false);
    }
    function onScroll() {
      setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  // ─── calendar helpers ────────────────────────────────────────────────────

  function buildCells() {
    const firstDow = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const cells: (number | null)[] = Array(firstDow).fill(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    return cells;
  }

  function isDayDisabled(day: number) {
    const dayStr = fmtDt(viewYear, viewMonth, day, 0, 0);
    const effMinDay = fmtDt(effMin.year, effMin.month, effMin.day, 0, 0);
    const maxDay = fmtDt(maxDt.year, maxDt.month, maxDt.day, 0, 0);
    return dayStr < effMinDay || dayStr > maxDay;
  }

  function getTimeSlots(y: number, m: number, d: number): string[] {
    const minS = fmtDt(effMin.year, effMin.month, effMin.day, effMin.hour, effMin.minute);
    const maxS = fmtDt(maxDt.year, maxDt.month, maxDt.day, maxDt.hour, maxDt.minute);
    const slots: string[] = [];
    for (let h = 0; h < 24; h++) {
      for (const min of [0, 30]) {
        const s = fmtDt(y, m, d, h, min);
        if (s >= minS && s <= maxS) slots.push(`${p2(h)}:${p2(min)}`);
      }
    }
    return slots;
  }

  function handleDayClick(day: number) {
    setSelYear(viewYear);
    setSelMonth(viewMonth);
    setSelDay(day);
    const slots = getTimeSlots(viewYear, viewMonth, day);
    if (slots.length === 0) return;
    const currentSlot = `${p2(selHour)}:${p2(selMinute)}`;
    if (!slots.includes(currentSlot)) {
      const [h, min] = slots[0].split(":").map(Number);
      setSelHour(h);
      setSelMinute(min);
    }
  }

  function handleTimeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const [h, m] = e.target.value.split(":").map(Number);
    setSelHour(h);
    setSelMinute(m);
  }

  function confirmSelection() {
    if (selYear == null || selMonth == null || selDay == null) return;
    onChange(fmtDt(selYear, selMonth, selDay, selHour, selMinute));
    setOpen(false);
  }

  function prevMonth() {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
  }

  function nextMonth() {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
  }

  const canPrev =
    viewYear > effMin.year ||
    (viewYear === effMin.year && viewMonth > effMin.month);
  const canNext =
    viewYear < maxDt.year ||
    (viewYear === maxDt.year && viewMonth < maxDt.month);

  const cells = buildCells();
  const timeSlots =
    selYear != null && selMonth != null && selDay != null
      ? getTimeSlots(selYear, selMonth, selDay)
      : [];
  const selectedTimeStr = `${p2(selHour)}:${p2(selMinute)}`;
  const effectiveTimeValue = timeSlots.includes(selectedTimeStr)
    ? selectedTimeStr
    : (timeSlots[0] ?? "");

  const displayValue = value ? `${value.slice(0, 10)}  ${value.slice(11, 16)}` : null;

  // ─── render ──────────────────────────────────────────────────────────────

  const popup = open ? (
    <div
      ref={popupRef}
      style={popupStyle}
      className="rounded-xl border border-outline bg-surface-2 shadow-2xl overflow-hidden"
    >
      {/* Month navigation */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-outline">
        <button
          type="button"
          onClick={prevMonth}
          disabled={!canPrev}
          className="w-7 h-7 flex items-center justify-center rounded-md text-muted hover:text-foreground hover:bg-surface-3 disabled:opacity-20 transition text-base"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-foreground select-none">
          {MONTH_NAMES[viewMonth]} {viewYear}
        </span>
        <button
          type="button"
          onClick={nextMonth}
          disabled={!canNext}
          className="w-7 h-7 flex items-center justify-center rounded-md text-muted hover:text-foreground hover:bg-surface-3 disabled:opacity-20 transition text-base"
        >
          ›
        </button>
      </div>

      {/* Day grid */}
      <div className="px-2.5 pt-2 pb-1">
        <div className="grid grid-cols-7 mb-0.5">
          {DAY_ABBR.map((d) => (
            <div
              key={d}
              className="text-center text-[9px] text-muted/50 font-medium py-1 select-none"
            >
              {d}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-y-0.5">
          {cells.map((cell, i) => {
            if (cell == null) return <div key={`e-${i}`} />;
            const disabledDay = isDayDisabled(cell);
            const isSelected =
              selYear === viewYear && selMonth === viewMonth && selDay === cell;
            return (
              <button
                key={cell}
                type="button"
                disabled={disabledDay}
                onClick={() => handleDayClick(cell)}
                className={`py-1.5 text-[11px] rounded-md transition leading-none ${
                  isSelected
                    ? "bg-primary text-background font-semibold"
                    : disabledDay
                      ? "text-muted/20 cursor-not-allowed"
                      : "text-foreground/80 hover:bg-surface-4 hover:text-foreground"
                }`}
              >
                {cell}
              </button>
            );
          })}
        </div>
      </div>

      {/* Time selector */}
      {selDay != null && timeSlots.length > 0 && (
        <div className="border-t border-outline px-3 py-2.5">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted w-8 flex-shrink-0">Time</span>
            <select
              className="flex-1 rounded-lg border border-outline bg-surface-3 px-2 py-1.5 text-xs text-foreground font-mono cursor-pointer focus:outline-none focus:border-primary/50"
              value={effectiveTimeValue}
              onChange={handleTimeChange}
            >
              {timeSlots.map((slot) => (
                <option key={slot} value={slot}>
                  {slot}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Confirm */}
      <div className="px-3 pb-3 pt-1.5">
        <button
          type="button"
          disabled={selDay == null || timeSlots.length === 0}
          onClick={confirmSelection}
          className="w-full rounded-lg border border-primary/35 bg-primary/15 py-1.5 text-[11px] font-semibold text-primary hover:bg-primary/25 disabled:opacity-40 disabled:cursor-not-allowed transition active:scale-[0.98]"
        >
          Confirm
        </button>
      </div>
    </div>
  ) : null;

  return (
    <div>
      <label className="text-[10px] text-muted block mb-1.5">
        {label} {required && <span className="text-danger">*</span>}
      </label>

      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition ${
          open
            ? "border-primary/50 bg-surface-3 text-foreground"
            : "border-outline bg-surface-2 hover:bg-surface-3 text-muted hover:text-foreground"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        <span className={displayValue ? "text-foreground font-mono tracking-wide" : "text-muted"}>
          {displayValue ?? "Pick date & time…"}
        </span>
        <svg
          className={`w-3 h-3 flex-shrink-0 opacity-50 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 16 16"
        >
          <path
            d="M3 6l5 5 5-5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {typeof window !== "undefined" && createPortal(popup, document.body)}
    </div>
  );
}
