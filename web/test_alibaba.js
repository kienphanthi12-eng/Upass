const apiKey = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIzMDUwMDEwNiIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3OTU2MDEwMywiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiMzdkOTVlZTItMzhhNC00OWJmLWJjYzAtN2UzNTU5ZmIxNzY0IiwiZW1haWwiOiIiLCJleHAiOjE3ODczMzYxMDN9.6qALe67rQjFtHppaMRuSH4glt6bLwHgepwVcNXqnFv4QHG0OaMwTWV3K5HUvwX6U-OHldIluDEnSfzc3ELYsnQ";
const endpoint = "https://mineru.net/api/v4/file-urls/batch";

async function testLang(lang) {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        files: [{ name: "test.pdf", data_id: "test.pdf" }],
        enable_formula: true,
        enable_table: true,
        language: lang,
        is_ocr: true,
      })
    });
    const json = await res.json();
    console.log(`Response for '${lang}':`, json.code === 0 ? "Success" : json.msg);
  } catch (err) {
    console.error(`Error for '${lang}':`, err);
  }
}

async function run() {
  await testLang("auto");
  await testLang("vi");
}

run();
