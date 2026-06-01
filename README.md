# Malm Queen → Murphy Bed Conversion

OSB cabinet + direct-bracket VEVOR kit conversion of an IKEA Malm Queen bed frame into a wall-mounted Murphy bed. Cost-optimized design: ~$260–330 in materials.

## Contents

| Path | Description |
|---|---|
| `design/design.html` | Full design doc with SVG diagrams, construction steps, shopping list |
| `design/design.md` | Same content in Markdown |
| `design/diagrams/` | 6 dimensioned SVG diagrams (assembly, panels, mounting, exploded, ceiling, bed-open) |
| `design/3d/` | Programmatic CadQuery 3D model (27-part assembly, STL/STEP, Three.js viewer) |
| `ref/` | Original VEVOR kit manual and IKEA MALM assembly instructions (PDFs) |

## 3D Viewer

```bash
./view.sh          # starts server + opens browser
# or manually:    python3 -m http.server 8080
# then open:      http://localhost:8080/design/3d/viewer.html
```

Opens a Three.js viewer with the full assembly in 3D. Orbit with mouse, switch between Open / Stored / Cabinet Only / Exploded views.

> Opening `design/3d/viewer.html` directly via `file://` will fail due to browser CORS policy. Use `./view.sh` to serve it locally.

## License

MIT — see [LICENSE](LICENSE).

The PDFs in `ref/` are copyright their respective owners (VEVOR/BAGUO and IKEA) and are included for reference only.
