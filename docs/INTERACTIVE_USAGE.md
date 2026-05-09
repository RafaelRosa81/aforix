# Interactive Usage and Launchers

## Objective

Interactive workflows provide a simplified operational interface for Aforix.

The goal is to support:

- operational users;
- reproducible workflows;
- launcher-based execution;
- reduced CLI complexity.

---

# Interactive Principles

Interactive workflows:

- must not implement processing logic;
- must reuse the same registry and runner;
- may generate temporary batch definitions;
- may execute registered commands directly.

---

# Planned Interactive Commands

```bash
aforix normalize interactive
aforix validate interactive
aforix export interactive
aforix analyze interactive
aforix batch interactive
```

---

# Launchers

## Purpose

Launchers simplify:

- shell startup;
- conda activation;
- environment activation;
- repo navigation;
- interactive command startup.

---

# Planned Structure

```text
launchers/
├── windows/
│   ├── aforix_shell.bat
│   ├── batch_interactive.bat
│   ├── normalize_interactive.bat
│   ├── validate_interactive.bat
│   ├── export_tables_interactive.bat
│   └── analyze_interactive.bat
│
├── linux/
│   ├── aforix_shell.sh
│   └── ...
```

---

# Expected Behavior

Correct behavior:

```text
open shell
activate aforix environment
run interactive workflow
keep shell open
```

Incorrect behavior:

```text
open shell
execute
close immediately
```

---

# Session-Oriented Usage

Once the aforix environment is activated, users should continue using the same shell session.

The launcher is only the entry point.

---

# Future Directions

Potential future features:

- TUI interface
- menu navigation
- graphical launcher
- dashboard
- workflow templates
