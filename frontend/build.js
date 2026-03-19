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
};

async function build() {
  const dirs = fs.readdirSync(packagesDir).filter((d) => {
    return fs.statSync(path.join(packagesDir, d)).isDirectory();
  });

  for (const dir of dirs) {
    const pkgPath = path.join(packagesDir, dir, "package.json");
    if (!fs.existsSync(pkgPath)) continue;

    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));

    // Skip packages marked with buildConfig.skip (e.g. shared utils)
    if (pkg.buildConfig?.skip) continue;

    const entryPoint = path.join(packagesDir, dir, "src/index.js");
    if (!fs.existsSync(entryPoint)) {
      console.warn(`  skip ${dir} (no src/index.js)`);
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
