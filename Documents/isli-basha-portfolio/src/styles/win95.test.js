import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(resolve(here, 'win95.css'), 'utf8');

function ruleBody(selector) {
  const pattern = new RegExp(
    `${selector.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\$&')}\\s*\\{([^}]*)\\}`,
  );
  const match = css.match(pattern);
  return match ? match[1] : '';
}

describe('contact window CSS', () => {
  it('anchors .win-contact in the desktop layout without stretching', () => {
    const body = ruleBody('.win-contact');
    expect(body).toMatch(/top\s*:\s*\d+%/);
    expect(body).toMatch(/right\s*:\s*\d+%/);
    expect(body).toMatch(/width\s*:\s*\d+%/);
  });
});

describe('desktop layout CSS', () => {
  it('locks the desktop area height inside the desktop media query', () => {
    expect(css).toMatch(/@media\s*\(min-width:\s*1024px\)/);
    expect(css).toMatch(/\.desktop-area[\s\S]*?height\s*:\s*calc\(100vh\s*-\s*34px\)/);
  });

  it('does not cap default window content height (no scroll on initial open)', () => {
    // The desktop media query must not force max-height: <n>vh on the
    // default window content: windows should size naturally to fit content.
    const desktopBlock = css.match(
      /@media\s*\(min-width:\s*1024px\)\s*\{([\s\S]+)\}\s*$/m,
    );
    const block = desktopBlock ? desktopBlock[1] : css;
    expect(block).not.toMatch(
      /\.win-(?:about|projects|stack|contact)\s+\.win95-window__content\s*\{[^}]*max-height\s*:\s*\d+vh/,
    );
  });
});

describe('maximized window CSS', () => {
  it('defines a rule for the maximized modifier that fills the viewport', () => {
    const body = ruleBody('.win95-window--maximized');
    expect(body.length).toBeGreaterThan(0);
    expect(body).toMatch(/position\s*:\s*fixed/);
  });
});

function topLevelRuleBody(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(?:^|\\n)${escaped}\\s*\\{([^}]*)\\}`);
  const match = css.match(pattern);
  return match ? match[1] : '';
}

function mobileCssBlock() {
  const idx = css.indexOf('@media (max-width: 1023px)');
  if (idx === -1) return '';
  const after = css.slice(idx);
  // Slice up to the next top-level @media rule
  const nextMedia = after.indexOf('\n@media', 1);
  return nextMedia === -1 ? after : after.slice(0, nextMedia);
}

describe('mobile responsive polish', () => {
  it('removes sticky note rotation in the mobile breakpoint', () => {
    const block = mobileCssBlock();
    expect(block).toContain('.sticky-note');
    expect(block).toMatch(/transform\s*:\s*none/);
  });

  it('makes windows full-width on mobile to prevent horizontal clipping', () => {
    const block = mobileCssBlock();
    expect(block).toContain('.win95-window');
    expect(block).toMatch(/width\s*:\s*100%/);
  });

  it('prevents horizontal scrolling on the mobile desktop area', () => {
    const block = mobileCssBlock();
    expect(block).toMatch(/overflow-x\s*:\s*hidden/);
  });
});

describe('window flex layout for natural resize', () => {
  it('window is a flex column so the content area fills the chrome', () => {
    const body = topLevelRuleBody('.win95-window');
    expect(body).toMatch(/display\s*:\s*flex/);
    expect(body).toMatch(/flex-direction\s*:\s*column/);
  });

  it('window content stretches to fill remaining vertical space', () => {
    const body = topLevelRuleBody('.win95-window__content');
    expect(body).toMatch(/flex\s*:\s*1/);
    expect(body).toMatch(/min-height\s*:\s*0/);
  });
});
