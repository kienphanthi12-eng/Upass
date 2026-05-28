const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;
const text = "Độ dài vectơ $\\scriptstyle { \\overrightarrow { u } } = { \\overrightarrow { A B } } + { \\overrightarrow { A D } } + { \\overrightarrow { A ^ { \\prime } C ^ { \\prime } } }$ bằng";
const segments = text.split(MATH_RE);
console.log(segments);
