/**
 * Telegram webhook (Cloudflare Workers, бесплатный тариф, без карты, всегда включён).
 *
 * Когда Стас отвечает (Reply) на сообщение бота kwork-monitor со своим отредактированным
 * текстом отклика, Telegram присылает сюда update с message.reply_to_message — это
 * оригинальное уведомление, в котором уже есть ссылка на заказ (https://kwork.ru/projects/...).
 * Воркер достаёт ссылку через regex и прикрепляет такую же кнопку "Перейти к заказу"
 * к отредактированному сообщению Стаса — без отдельной базы данных, ссылка и так лежит
 * в тексте исходного сообщения.
 *
 * TELEGRAM_BOT_TOKEN передаётся как секрет окружения Worker'а (wrangler secret put).
 */

const KWORK_URL_RE = /https:\/\/kwork\.ru\/projects\/\d+/;

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("ok", { status: 200 });
    }

    const update = await request.json();
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
