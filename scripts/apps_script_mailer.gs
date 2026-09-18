// Google Apps Script web app that sends email from the Gmail account it is deployed under.
// Paste into script.google.com, set SECRET, then Deploy > New deployment > Web app
// (Execute as: Me, Who has access: Anyone) and copy the /exec URL.

const SECRET = "CHANGE-ME"; // must match APPS_SCRIPT_SECRET on the server

function doPost(e) {
  const reply = (obj) =>
    ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);

  let data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return reply({ ok: false, error: "bad json" });
  }
  if (data.secret !== SECRET) {
    return reply({ ok: false, error: "unauthorized" });
  }
  try {
    MailApp.sendEmail({
      to: data.to,
      subject: data.subject,
      body: data.text,
      name: data.from_name || "coroutines",
    });
    return reply({ ok: true, remaining: MailApp.getRemainingDailyQuota() });
  } catch (err) {
    return reply({ ok: false, error: String(err) });
  }
}
