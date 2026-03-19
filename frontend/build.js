const esbuild = require("esbuild");
const path = require("path");
const fs = require("fs");

const packagesDir = path.resolve(__dirname, "packages");
const outdir = path.resolve(__dirname, "../streamlit_ai_elements/assets");

const shared = {
  bundle: true,
  format: "esm",
  minify: true,
  target: ["es2020"],
  sourcemap: false,
  loader: {
    ".css": "text",
  },
};

function buildExcalidrawCss() {
  const cssPath = path.resolve(
    __dirname,
    "node_modules/@excalidraw/excalidraw/dist/prod/index.css",
  );

  if (!fs.existsSync(cssPath)) {
    return;
  }

  const raw = fs.readFileSync(cssPath, "utf-8");
  const stripped = raw
    .replace(/^@charset[^;]+;/, "")
    .replace(/@font-face\{[^}]+\}/g, "");

  const custom = `
#_r.ai-elements-excalidraw-root {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 420px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(76, 110, 245, 0.08), transparent 36%),
    linear-gradient(180deg, #fcfcfd 0%, #f8fafc 100%);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
}

#_r.ai-elements-excalidraw-root .ai-elements-excalidraw-mount {
  position: relative;
  width: 100%;
  height: 100%;
}

#_r.ai-elements-excalidraw-root.ai-elements-excalidraw-hide-ui .App-menu,
#_r.ai-elements-excalidraw-root.ai-elements-excalidraw-hide-ui .layer-ui__wrapper__footer,
#_r.ai-elements-excalidraw-root.ai-elements-excalidraw-hide-ui .main-menu-trigger,
#_r.ai-elements-excalidraw-root.ai-elements-excalidraw-hide-ui .help-icon,
#_r.ai-elements-excalidraw-root.ai-elements-excalidraw-hide-ui .undo-redo-buttons,
#_r.ai-elements-excalidraw-root.ai-elements-excalidraw-hide-ui .FixedSideContainer {
  display: none !important;
}
`;

  fs.writeFileSync(
    path.join(outdir, "excalidraw-editor.css"),
    `${stripped}\n${custom}\n`,
    "utf-8",
  );
}

function resolveEntryPoint(dir) {
  const tsxEntry = path.join(packagesDir, dir, "src/index.tsx");
  if (fs.existsSync(tsxEntry)) {
    return tsxEntry;
  }

  const tsEntry = path.join(packagesDir, dir, "src/index.ts");
  if (fs.existsSync(tsEntry)) {
    return tsEntry;
  }

  const jsEntry = path.join(packagesDir, dir, "src/index.js");
  if (fs.existsSync(jsEntry)) {
    return jsEntry;
  }

  return null;
}

async function build() {
  buildExcalidrawCss();

  const dirs = fs.readdirSync(packagesDir).filter((d) => {
    return fs.statSync(path.join(packagesDir, d)).isDirectory();
  });

  for (const dir of dirs) {
    const pkgPath = path.join(packagesDir, dir, "package.json");
    if (!fs.existsSync(pkgPath)) continue;

    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));

    // Skip packages marked with buildConfig.skip (e.g. shared utils)
    if (pkg.buildConfig?.skip) continue;

    const entryPoint = resolveEntryPoint(dir);
    if (!entryPoint) {
      console.warn(`  skip ${dir} (no src/index.tsx, src/index.ts, or src/index.js)`);
      continue;
    }

    // Output filename matches the directory name → Python _load_asset() expects this
    const outfile = path.join(outdir, `${dir}.js`);

    await esbuild.build({
      ...shared,
      entryPoints: [entryPoint],
      outfile,
    });

    const size = (fs.statSync(outfile).size / 1024).toFixed(0);
    console.log(`  ${dir}.js  (${size} KB)`);
  }

  console.log(`\nBuilt to ${outdir}`);
}

build().catch((e) => {
  console.error(e);
  process.exit(1);
});
