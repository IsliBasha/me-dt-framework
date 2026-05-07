import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';

describe('App game desktop icons', () => {
  it('shows minesweeper and snake icons on the desktop', () => {
    render(<App />);
    expect(
      screen.getByRole('button', { name: /minesweeper\.exe/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /snake\.exe/i }),
    ).toBeInTheDocument();
  });

  it('does not render the minesweeper or snake windows on load', () => {
    render(<App />);
    expect(
      screen.queryByRole('region', { name: /minesweeper\.exe/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: /snake\.exe/i }),
    ).not.toBeInTheDocument();
  });

  it('opens the minesweeper window only after its icon is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(
      screen.getByRole('button', { name: /minesweeper\.exe/i }),
    );

    expect(
      screen.getByRole('region', { name: /minesweeper\.exe/i }),
    ).toBeInTheDocument();
  });

  it('opens the snake window only after its icon is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /snake\.exe/i }));

    expect(
      screen.getByRole('region', { name: /snake\.exe/i }),
    ).toBeInTheDocument();
  });
});

describe('App initial desktop state', () => {
  it('does not render any of the content windows on load', () => {
    render(<App />);
    expect(
      screen.queryByRole('region', { name: 'about.txt' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'projects' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'stack.cmd' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'contact.exe' }),
    ).not.toBeInTheDocument();
  });

  it('renders a stack.cmd icon on the desktop', () => {
    render(<App />);
    expect(
      screen.getByRole('button', { name: 'stack.cmd' }),
    ).toBeInTheDocument();
  });

  it('opens the about window only after the about.txt icon is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'about.txt' }));
    expect(
      screen.getByRole('region', { name: 'about.txt' }),
    ).toBeInTheDocument();
  });

  it('opens the stack window only after the stack.cmd icon is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'stack.cmd' }));
    expect(
      screen.getByRole('region', { name: 'stack.cmd' }),
    ).toBeInTheDocument();
  });
});

describe('App desktop labels', () => {
  it('labels desktop icons with the rebranded filenames', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: 'about.txt' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'projects' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'about.exe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'projects.exe' })).not.toBeInTheDocument();
  });
});

describe('Menu bar items — decorative only', () => {
  it('clicking a menu item in the about window does not open a dialog', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'about.txt' }));
    const [first] = screen.getAllByRole('menuitem');
    await user.click(first);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('clicking a menu item in the projects window does not open a dialog', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'projects' }));
    const [first] = screen.getAllByRole('menuitem');
    await user.click(first);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('clicking a menu item in the contact window does not open a dialog', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'contact.exe' }));
    const [first] = screen.getAllByRole('menuitem');
    await user.click(first);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('clicking a menu item in the resume window does not open a dialog', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'resume.pdf' }));
    const [first] = screen.getAllByRole('menuitem');
    await user.click(first);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('submitting the contact form still shows a confirmation dialog', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'contact.exe' }));
    await user.type(screen.getByRole('textbox'), 'Hello');
    await user.click(screen.getByRole('button', { name: /send message/i }));
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });
});

describe('Desktop icon — resume.pdf opens window', () => {
  it('resume.pdf icon is a button (not a link) and opens the resume window', async () => {
    const user = userEvent.setup();
    render(<App />);
    const icon = screen.getByRole('button', { name: 'resume.pdf' });
    expect(icon).toBeInTheDocument();
    await user.click(icon);
    expect(
      screen.getByRole('region', { name: /resume\.pdf/i }),
    ).toBeInTheDocument();
  });
});
