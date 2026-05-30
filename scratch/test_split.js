
const fs = require('fs');
const path = require('path');

// Port splitNormalizedText from deepseek.ts to JavaScript
function splitNormalizedText(normalizedText) {
  const partPat = /==PHAN\s*(\d+)==/gi;
  const splits = [...normalizedText.matchAll(partPat)];

  const partsMap = new Map();
  let maxSeen = 0;

  for (let i = 0; i < splits.length; i++) {
    const partNum = parseInt(splits[i][1]);
    const start = splits[i].index + splits[i][0].length;
    const end = i + 1 < splits.length ? splits[i + 1].index : normalizedText.length;
    const text = normalizedText.slice(start, end).trim();

    if (partNum > maxSeen) {
      maxSeen = partNum;
      partsMap.set(partNum, text);
    } else {
      const existing = partsMap.get(maxSeen) || '';
      partsMap.set(maxSeen, existing + '\n\n' + text);
    }
  }

  if (partsMap.size === 0) partsMap.set(1, normalizedText);

  console.log("partsMap size:", partsMap.size);
  console.log("partsMap keys:", [...partsMap.keys()]);

  const questions = [];
  for (const partNum of [...partsMap.keys()].sort()) {
    const partText = partsMap.get(partNum);
    const cauPat = /(?:^|\n)\s*\[CAU\s+(\d+)\]/gi;
    const matches = [...partText.matchAll(cauPat)];
    console.log(`Part \${partNum} matches count:`, matches.length);

    for (let i = 0; i < matches.length; i++) {
      const qNum = parseInt(matches[i][1]);
      const start = matches[i].index;
      const end = i + 1 < matches.length ? matches[i + 1].index : partText.length;
      const rawContent = partText.slice(start, end).trim();

      questions.push({
        part: `part_\${partNum}`,
        question_index: qNum,
        raw_content: rawContent,
      });
    }
  }

  return questions;
}

const text = fs.readFileSync('scratch/job_normalized.md', 'utf-8');
const qs = splitNormalizedText(text);
console.log("Total extracted questions:", qs.length);
if (qs.length > 0) {
  console.log("First question sample:", qs[0]);
}
