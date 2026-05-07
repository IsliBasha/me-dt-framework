const MENUS = ['File', 'Edit', 'View', 'Window', 'Help'];

function FloppyIcon() {
  return (
    <svg viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true" width="16" height="16">
      <rect x="1" y="1" width="14" height="14" fill="#000080" />
      <rect x="2" y="6" width="12" height="8" fill="#c0c0c0" />
      <rect x="5" y="1" width="6" height="5" fill="#808080" />
      <rect x="6" y="2" width="4" height="3" fill="#404040" />
      <rect x="3" y="8" width="10" height="1" fill="#808080" />
      <rect x="3" y="10" width="10" height="1" fill="#808080" />
    </svg>
  );
}

function PrinterIcon() {
  return (
    <svg viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true" width="16" height="16">
      <rect x="4" y="1" width="8" height="4" fill="#ffffff" />
      <rect x="4" y="1" width="8" height="1" fill="#808080" />
      <rect x="4" y="4" width="1" height="1" fill="#808080" />
      <rect x="11" y="4" width="1" height="1" fill="#808080" />
      <rect x="1" y="5" width="14" height="7" fill="#808080" />
      <rect x="2" y="6" width="12" height="5" fill="#a0a0a0" />
      <rect x="3" y="10" width="10" height="5" fill="#ffffff" />
      <rect x="3" y="10" width="10" height="1" fill="#808080" />
      <rect x="11" y="7" width="2" height="2" fill="#00c800" />
    </svg>
  );
}

export function ResumeViewer() {
  const handlePrint = () => {
    const iframe = document.getElementById('resume-pdf-iframe');
    try {
      iframe?.contentWindow?.print();
    } catch {
      window.open('/resume.pdf', '_blank');
    }
  };

  return (
    <>
      <div className="explorer-menubar" role="menubar">
        {MENUS.map((item) => (
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
      <div className="pdf-toolbar" role="toolbar" aria-label="PDF controls">
        <a
          href="/resume.pdf"
          download="isli-basha-resume.pdf"
          className="pdf-toolbar-btn"
          title="Save a Copy"
          aria-label="Download resume PDF"
        >
          <FloppyIcon />
        </a>
        <span className="pdf-toolbar-sep" aria-hidden="true" />
        <button
          type="button"
          className="pdf-toolbar-btn"
          title="Print"
          aria-label="Print resume"
          onClick={handlePrint}
        >
          <PrinterIcon />
        </button>
      </div>
      <div className="pdf-viewer-wrap">
        <iframe
          id="resume-pdf-iframe"
          className="pdf-viewer-iframe"
          src="/resume.pdf"
          title="Resume PDF"
        />
      </div>
      <div className="pdf-statusbar">
        <span>resume.pdf</span>
        <a
          href="/resume.pdf"
          download="isli-basha-resume.pdf"
          className="pdf-download-link"
        >
          Save a Copy
        </a>
      </div>
    </>
  );
}
