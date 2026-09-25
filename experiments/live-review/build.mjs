import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const dependencies = path.resolve(process.argv[2]);
const output = path.resolve(process.argv[3]);
const require = createRequire(path.join(dependencies, "package.json"));
const { build } = require("esbuild");
await build({
  entryPoints: [path.join(here, "toolbar.jsx")],
  bundle: true,
  outfile: output,
  minify: true,
  nodePaths: [path.join(dependencies, "node_modules")],
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "eof",
});
