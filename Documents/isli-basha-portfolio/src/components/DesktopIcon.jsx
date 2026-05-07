import { useCallback, useEffect, useRef, useState } from 'react';
import { useWindowStack } from '../context/windowStackContext.js';
import { useIconPosition } from '../hooks/useIconPosition.js';

const DESKTOP_MIN_WIDTH = 1024;

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(min-width: ${DESKTOP_MIN_WIDTH}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${DESKTOP_MIN_WIDTH}px)`);
    const onChange = (e) => setIsDesktop(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  return isDesktop;
}

function Glyph({ kind }) {
  if (kind === 'minesweeper') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="2" y="2" width="28" height="28" fill="#c0c0c0" stroke="#000000" />
        <rect x="4" y="4" width="24" height="24" fill="#808080" />
        <rect x="5" y="5" width="22" height="22" fill="#c0c0c0" />
        <rect x="10" y="10" width="12" height="12" fill="#000000" />
        <rect x="12" y="12" width="8" height="8" fill="#ff0000" />
        <rect x="14" y="8" width="4" height="2" fill="#000000" />
        <rect x="22" y="14" width="2" height="4" fill="#000000" />
        <rect x="14" y="22" width="4" height="2" fill="#000000" />
        <rect x="8" y="14" width="2" height="4" fill="#000000" />
      </svg>
    );
  }
  if (kind === 'snake') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="2" y="2" width="28" height="28" fill="#000000" stroke="#333333" />
        <rect x="6" y="20" width="4" height="4" fill="#33ff33" />
        <rect x="10" y="20" width="4" height="4" fill="#33ff33" />
        <rect x="14" y="20" width="4" height="4" fill="#33ff33" />
        <rect x="14" y="16" width="4" height="4" fill="#33ff33" />
        <rect x="14" y="12" width="4" height="4" fill="#33ff33" />
        <rect x="18" y="12" width="4" height="4" fill="#33ff33" />
        <rect x="22" y="8" width="4" height="4" fill="#ff3333" />
      </svg>
    );
  }
  if (kind === 'about') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="6" y="4" width="20" height="24" fill="#ffffff" stroke="#000000" />
        <rect x="8" y="7" width="16" height="1" fill="#808080" />
        <rect x="8" y="10" width="16" height="1" fill="#808080" />
        <rect x="8" y="13" width="10" height="1" fill="#808080" />
        <rect x="8" y="17" width="14" height="1" fill="#808080" />
        <rect x="8" y="20" width="12" height="1" fill="#808080" />
        <rect x="8" y="23" width="14" height="1" fill="#808080" />
      </svg>
    );
  }
  if (kind === 'projects') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="2" y="8" width="28" height="20" fill="#f4c430" stroke="#000000" />
        <rect x="2" y="5" width="13" height="4" fill="#f4c430" stroke="#000000" />
        <rect x="4" y="10" width="24" height="1" fill="#a8861e" />
      </svg>
    );
  }
  if (kind === 'contact') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="3" y="8" width="26" height="18" fill="#ffffff" stroke="#000000" />
        <polyline
          points="3,8 16,20 29,8"
          fill="none"
          stroke="#000000"
          strokeWidth="1"
        />
      </svg>
    );
  }
  if (kind === 'stack') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="2" y="4" width="28" height="22" fill="#0c0c0c" stroke="#000000" />
        <rect x="2" y="4" width="28" height="3" fill="#c0c0c0" />
        <rect x="4" y="5" width="1" height="1" fill="#1a1a2e" />
        <rect x="6" y="5" width="1" height="1" fill="#1a1a2e" />
        <rect x="8" y="5" width="1" height="1" fill="#1a1a2e" />
        <text x="5" y="16" fontFamily="monospace" fontSize="7" fill="#33ff33">
          C:\
        </text>
        <text x="5" y="23" fontFamily="monospace" fontSize="7" fill="#33ff33">
          &gt;_
        </text>
      </svg>
    );
  }
  if (kind === 'resume') {
    return (
      <svg viewBox="0 0 32 32" shapeRendering="crispEdges" aria-hidden="true">
        <rect x="6" y="4" width="20" height="24" fill="#ffffff" stroke="#000000" />
        <rect x="20" y="4" width="6" height="6" fill="#dfdfdf" stroke="#000000" />
        <rect x="9" y="14" width="14" height="1" fill="#cc1616" />
        <rect x="9" y="17" width="14" height="1" fill="#808080" />
        <rect x="9" y="20" width="10" height="1" fill="#808080" />
        <rect x="9" y="23" width="12" height="1" fill="#808080" />
      </svg>
    );
  }
  return null;
}

export function DesktopIcon({ kind, label, target, href, defaultPos = { x: 16, y: 16 } }) {
  const { bringToFront } = useWindowStack();
  const isDesktop = useIsDesktop();
  const { pos, setPos, savePosition } = useIconPosition(kind, defaultPos, {
    enabled: isDesktop,
  });

  const dragRef = useRef(null);
  const suppressClickRef = useRef(false);

  const handlePointerDown = useCallback(
    (e) => {
      if (!isDesktop) return;
      if (e.button !== 0) return;
      if (href) return;
      e.preventDefault();
      dragRef.current = {
        startX: e.clientX - pos.x,
        startY: e.clientY - pos.y,
        pointerId: e.pointerId,
        lastPos: pos,
        moved: false,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [isDesktop, href, pos],
  );

  const handlePointerMove = useCallback(
    (e) => {
      if (!dragRef.current) return;
      const next = {
        x: Math.max(0, Math.min(window.innerWidth - 80, e.clientX - dragRef.current.startX)),
        y: Math.max(0, Math.min(window.innerHeight - 114, e.clientY - dragRef.current.startY)),
      };
      dragRef.current.moved = true;
      dragRef.current.lastPos = next;
      setPos(next);
    },
    [setPos],
  );

  const handlePointerUp = useCallback(
    (e) => {
      if (!dragRef.current) return;
      const { moved, pointerId, lastPos } = dragRef.current;
      try {
        e.currentTarget.releasePointerCapture(pointerId);
      } catch {
        /* already released */
      }
      dragRef.current = null;
      if (moved) {
        savePosition(lastPos);
        suppressClickRef.current = true;
      }
    },
    [savePosition],
  );

  const handleClick = useCallback(
    (e) => {
      if (suppressClickRef.current) {
        suppressClickRef.current = false;
        return;
      }
      if (href) return;
      e.preventDefault();
      if (!target) return;
      bringToFront(target);
      const node = document.getElementById(target);
      if (node) {
        node.scrollIntoView({ behavior: 'smooth', block: 'center' });
        node.focus({ preventScroll: true });
      }
    },
    [bringToFront, target, href],
  );

  const Tag = href ? 'a' : 'button';
  const extra = href ? { href, rel: 'noopener' } : { type: 'button' };

  const style = isDesktop
    ? { position: 'absolute', left: pos.x, top: pos.y }
    : undefined;

  return (
    <Tag
      {...extra}
      className="win95-desktop-icon"
      aria-label={label}
      style={style}
      onClick={handleClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <span className="win95-desktop-icon__glyph">
        <Glyph kind={kind} />
      </span>
      <span>{label}</span>
    </Tag>
  );
}
