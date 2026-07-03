/**
 * Telegram webhook (Cloudflare Workers, бесплатный тариф, без карты, всегда включён).
 *
 * Обрабатывает два типа updates:
 *
 * 1. Reply на сообщение бота — Стас отредактировал черновик и отвечает своим текстом.
 *    Воркер достаёт ссылку на заказ из оригинального сообщения и прикрепляет кнопку
 *    "Перейти к заказу" к отредактированному сообщению.
 *
 * 2. Callback от кнопки "✍️ Написать отклик" — парсит данные заказа из сообщения бота
 *    и запускает GitHub Actions workflow draft_on_demand.yml, который генерирует черновик
 *    через claude CLI и присылает его реплаем на это же сообщение.
 *
 * Secrets в окружении Worker'а (wrangler secret put):
 *   TELEGRAM_BOT_TOKEN — токен бота
 *   GITHUB_PAT         — Personal Access Token с scope "workflow"
 */

const KWORK_URL_RE = /https:\/\/kwork\.ru\/projects\/\d+/;
const GITHUB_REPO = "excusee/kwork-monitor";
const WORKFLOW_FILE = "draft_on_demand.yml";

async function answerCallback(token, callbackQueryId, text) {
  await fetch(`https://api.telegram.org/bot${token}/answerCallbackQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId, text }),
  });
}

async function triggerWorkflow(pat, inputs) {
  const resp = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${pat}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main", inputs }),
    }
  );
  return resp.ok;
}

function parseOrderFromText(text) {
  const titleMatch = text.match(/🆕 (.+)/);
  const urlMatch = text.match(/🔗 (https:\/\/kwork\.ru\/projects\/\d+)/);
  const budgetMatch = text.match(/💰 (.+)/);

  const title = titleMatch ? titleMatch[1].trim() : "";
  const url = urlMatch ? urlMatch[1].trim() : "";
  const budget = budgetMatch ? budgetMatch[1].trim() : "";

  // Описание — всё что после строки с URL и пустой строки
  const urlLineEnd = text.indexOf("\n", text.indexOf("🔗 "));
  const description = urlLineEnd !== -1
    ? text.slice(urlLineEnd + 2).trim()
    : "";

  return { title, url, budget, description };
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("ok", { status: 200 });
    }

    const update = await request.json();

    // --- Кнопка "✍️ Написать отклик" ---
    const cq = update.callback_query;
    if (cq && cq.data === "draft") {
      await answerCallback(env.TELEGRAM_BOT_TOKEN, cq.id, "⏳ Генерирую черновик...");

      const text = cq.message?.text || "";
      const { title, url, budget, description } = parseOrderFromText(text);
      const messageId = String(cq.message?.message_id || "");

      if (url) {
        await triggerWorkflow(env.GITHUB_PAT, {
          title,
          budget,
          description,
          url,
          message_id: messageId,
        });
      }

      return new Response("ok", { status: 200 });
    }

    // --- Reply с отредактированным черновиком ---
    const message = update.message;
    if (!message || !message.reply_to_message) {
      return new Response("ignored", { status: 200 });
    }

    const originalText = message.reply_to_message.text || "";
    const match = originalText.match(KWORK_URL_RE);
    if (!match) {
      return new Response("no url found", { status: 200 });
    }

    const projectUrl = match[0];

    await fetch(
      `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: message.chat.id,
          text: "✏️ Отредактированный вариант",
          reply_to_message_id: message.message_id,
          reply_markup: {
            inline_keyboard: [[{ text: "🔗 Перейти к заказу", url: projectUrl }]],
          },
        }),
      }
    );

    return new Response("ok", { status: 200 });
  },
};
