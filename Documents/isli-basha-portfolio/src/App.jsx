import { useCallback, useState } from 'react';
import { WindowStackProvider } from './context/WindowStack.jsx';
import { Window } from './components/Window.jsx';
import { Taskbar } from './components/Taskbar.jsx';
import { DesktopIcon } from './components/DesktopIcon.jsx';
import { ProjectCard } from './components/ProjectCard.jsx';
import { StackCmd } from './components/StackCmd.jsx';
import { StickyNote } from './components/StickyNote.jsx';
import { SystemDialog } from './components/SystemDialog.jsx';
import { Minesweeper } from './components/Minesweeper.jsx';
import { Snake } from './components/Snake.jsx';
import { BSOD } from './components/BSOD.jsx';
import { BootSequence } from './components/BootSequence.jsx';
import { Screensaver } from './components/Screensaver.jsx';
import { ContextMenu } from './components/ContextMenu.jsx';
import { ResumeViewer } from './components/ResumeViewer.jsx';
import { useInactivity } from './hooks/useInactivity.js';
import { projects } from './data/projects.js';

const WINDOW_ORDER = [
  'about',
  'projects',
  'stack',
  'contact',
  'resume',
  'minesweeper',
  'snake',
];
const INITIALLY_CLOSED = [
  'about',
  'projects',
  'stack',
  'contact',
  'resume',
  'minesweeper',
  'snake',
];

function NotepadAbout() {
  return (
    <>
      <div className="explorer-menubar" role="menubar">
        {['File', 'Edit', 'Format', 'View', 'Help'].map((item) => (
          <button
            key={item}
            type="button"
            className="explorer-menu-item"
            role="menuitem"
          >
            {item}
          </button>
        ))}
      </div>
      <div className="notepad-body">
        <h2 className="font-bold mb-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem' }}>
          ~/ whoami
        </h2>
        <p className="mb-2">
          I build software end-to-end — from the database schema up to the
          pixel on screen — from Tirana, Albania. I care a lot about how
          things feel under load, which usually means obsessing over the
          boring layers: caching, indexing, bundle size, render cost.
        </p>
        <p>
          Lately I am digging into edge computing and the parts of
          WebAssembly that actually ship.
        </p>
      </div>
      <div className="notepad-statusbar">
        <span>about.txt</span>
        <span>UTF-8</span>
      </div>
    </>
  );
}

function ContactExe() {
  return (
    <>
      <div className="explorer-menubar" role="menubar">
        {['File', 'Edit', 'Help'].map((item) => (
          <button
            key={item}
            type="button"
            className="explorer-menu-item"
            role="menuitem"
          >
            {item}
          </button>
        ))}
      </div>
      <div className="contact-body">
        <ul className="list-none m-0 p-0 flex flex-col gap-1.5">
          <li>
            <span
              className="inline-block w-[76px]"
              style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              Email:
            </span>
            <a href="mailto:islibasha1@gmail.com">islibasha1@gmail.com</a>
          </li>
          <li>
            <span
              className="inline-block w-[76px]"
              style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              GitHub:
            </span>
            <a
              href="https://github.com/IsliBasha"
              target="_blank"
              rel="noreferrer noopener"
            >
              github.com/IsliBasha
            </a>
          </li>
          <li>
            <span
              className="inline-block w-[76px]"
              style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              LinkedIn:
            </span>
            <a
              href="https://linkedin.com/in/islibasha"
              target="_blank"
              rel="noreferrer noopener"
            >
              linkedin.com/in/islibasha
            </a>
          </li>
        </ul>
        <ContactForm />
      </div>
      <div className="explorer-statusbar">Ready</div>
    </>
  );
}

function ProjectsExplorer({ projects: projectList }) {
  return (
    <>
      <div className="explorer-menubar" role="menubar">
        {['File', 'Edit', 'View', 'Help'].map((item) => (
          <button
            key={item}
            type="button"
            className="explorer-menu-item"
            role="menuitem"
          >
            {item}
          </button>
        ))}
      </div>
      <div className="explorer-address-bar">
        <span className="explorer-address-label">Address</span>
        <div
          className="explorer-address-field"
          aria-label="Current location: C:\ISLI\PROJECTS"
        >
          C:\ISLI\PROJECTS
        </div>
      </div>
      <div className="explorer-body">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {projectList.map((p) => (
            <ProjectCard
              key={p.id}
              name={p.name}
              description={p.description}
              stack={p.stack}
              href={p.href}
              iconType={p.iconType}
            />
          ))}
        </div>
      </div>
      <div className="explorer-statusbar">{projectList.length} object(s)</div>
    </>
  );
}

function ContactForm() {
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    setDialogOpen(true);
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 mt-3">
        <label
          htmlFor="contact-msg"
          className="text-xs uppercase tracking-wider text-[color:var(--c-gray-darker)]"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          Quick Message
        </label>
        <input
          id="contact-msg"
          name="message"
          type="text"
          className="win-field"
          placeholder="Type and press send…"
          maxLength={120}
          required
        />
        <div className="flex justify-end">
          <button type="submit" className="win-btn">
            Send Message
          </button>
        </div>
      </form>
      <SystemDialog
        open={dialogOpen}
        title="Message"
        message="Message sent. Thank you."
        onClose={() => setDialogOpen(false)}
      />
    </>
  );
}

function App() {
  const [screensaverOn, setScreensaverOn] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);

  const activateScreensaver = useCallback(() => setScreensaverOn(true), []);
  useInactivity(45_000, activateScreensaver);

  const handleContextMenu = useCallback((e) => {
    if (e.target.closest('.win95-window')) return;
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  }, []);

  return (
    <WindowStackProvider
      initialOrder={WINDOW_ORDER}
      initialClosed={INITIALLY_CLOSED}
    >
      {screensaverOn && (
        <Screensaver onDismiss={() => setScreensaverOn(false)} />
      )}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
        />
      )}
      <a href="#projects" className="skip-link">
        Skip to projects
      </a>
      <main className="desktop-area" onContextMenu={handleContextMenu}>
        <div className="desktop-icons" aria-label="Desktop shortcuts">
          <DesktopIcon kind="about"       label="about.txt"       target="about"       defaultPos={{ x: 16, y: 16  }} />
          <DesktopIcon kind="projects"    label="projects"        target="projects"    defaultPos={{ x: 16, y: 96  }} />
          <DesktopIcon kind="stack"       label="stack.cmd"       target="stack"       defaultPos={{ x: 16, y: 176 }} />
          <DesktopIcon kind="contact"     label="contact.exe"     target="contact"     defaultPos={{ x: 16, y: 256 }} />
          <DesktopIcon kind="resume"      label="resume.pdf"      target="resume"      defaultPos={{ x: 16, y: 336 }} />
          <DesktopIcon kind="minesweeper" label="minesweeper.exe" target="minesweeper" defaultPos={{ x: 16, y: 416 }} />
          <DesktopIcon kind="snake"       label="snake.exe"       target="snake"       defaultPos={{ x: 16, y: 496 }} />
        </div>

        <div className="sticky-note-wrap">
          <StickyNote />
        </div>

        <Window
          id="about"
          title="about.txt"
          className="win-about"
          bootDelayMs={0}
          contentClassName="win-about__content"
        >
          <NotepadAbout />
        </Window>

        <Window
          id="projects"
          title="projects"
          className="win-projects"
          bootDelayMs={120}
          contentClassName="win-projects__content"
        >
          <ProjectsExplorer projects={projects} />
        </Window>

        <Window
          id="stack"
          title="stack.cmd"
          className="win-stack"
          bootDelayMs={240}
          contentClassName="win-stack__content"
        >
          <StackCmd />
        </Window>

        <Window
          id="contact"
          title="contact.exe"
          className="win-contact"
          bootDelayMs={360}
          contentClassName="win-contact__content"
        >
          <ContactExe />
        </Window>

        <Window
          id="resume"
          title="resume.pdf - Adobe Acrobat"
          className="win-resume"
          bootDelayMs={0}
          contentClassName="win-resume__content"
        >
          <ResumeViewer />
        </Window>

        <Window
          id="minesweeper"
          title="minesweeper.exe"
          className="win-minesweeper"
          bootDelayMs={0}
          contentClassName="win-minesweeper__content"
        >
          <Minesweeper />
        </Window>

        <Window
          id="snake"
          title="snake.exe"
          className="win-snake"
          bootDelayMs={0}
          contentClassName="win-snake__content"
        >
          <Snake />
        </Window>
      </main>
      <Taskbar />
      <BSOD />
      <BootSequence />
    </WindowStackProvider>
  );
}

export default App;
