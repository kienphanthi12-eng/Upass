const fs = require('fs');
const data = JSON.parse(fs.readFileSync('db_output.json'));

const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;

for (const q of data) {
    if (q.content.includes('$')) {
        const segments = q.content.split(MATH_RE);
        for (let i = 0; i < segments.length; i += 2) {
            // These are PLAIN TEXT segments.
            // If they contain an unclosed $ or a $ that was meant to be math but had a newline, we can find it.
            if (segments[i].includes('$')) {
                console.log(`Question ${q.id} plain text segment contains '$':`);
                console.log(segments[i]);
                console.log('---');
            }
        }
    }
}
