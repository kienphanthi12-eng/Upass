const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;
const text = "Độ dài vectơ $\\scriptstyle { \\overrightarrow { u } } = { \\overrightarrow { A B } } + { \\overrightarrow { A D } } + { \\overrightarrow { A ^ { \\prime } C ^ { \\prime } } }$ bằng";
const text2 = "Độ dài vectơ $\\scriptstyle { \\overrightarrow { u } } = { \\overrightarrow { A B } } + { \\overrightarrow { A D } } + { \\overrightarrow { A ^ { \\prime } C ^ { \\prime } } }$ bằng".replace(/\\\\/g, '\\');
console.log("TEXT1:", text.split(MATH_RE));
console.log("TEXT2:", text2.split(MATH_RE));
