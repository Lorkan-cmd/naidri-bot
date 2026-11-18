import asyncio
import logging
import math
import os
import aiosqlite
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# --- ПЕРЕВОДЫ ---
TRANSLATIONS = {
    'ru': {
        'welcome_new': "👋 Добро пожаловать, {name}!\n\n🎁 Ты получил стартовый бонус: *{bonus} токенов*!\nТвой баланс: *{balance} токенов*.\n\nЭто бот взаимного пиара: выполняй задания, зарабатывай токены и продвигай свой канал!",
        'welcome_back': "С возвращением, {name}!\nТвой баланс: *{balance} токенов*.",
        'main_menu': "Главное меню:",
        'btn_tasks': "📋 Взять задание",
        'btn_create': "➕ Создать задание",
        'btn_my_tasks': "🗑 Мои задания",
        'btn_balance': "💰 Баланс и пополнение",
        'btn_top': "🏆 ТОП месяца",
        'btn_referrals': "👥 Рефералы",
        'btn_support': "🛎 Поддержка",
        'btn_lang': "🌐 Язык",
        'btn_promo': "🎁 Промокод",
        'btn_back': "🔙 Назад",
        'btn_menu': "🔙 В меню",
        'btn_cancel': "❌ Отмена",
        'btn_confirm': "✅ Подтвердить",
        'btn_delete': "🗑 Удалить #{id}",
        'no_tasks': "📋 Сейчас нет доступных заданий. Попробуй позже!",
        'no_my_tasks': "📋 У тебя нет активных заданий.",
        'top_empty': "🏆 В этом месяце ещё никто не заработал токенов. Стань первым! 🚀",
        'no_transactions': "📜 У тебя пока нет транзакций.",
        'report_sent': "✅ Отчёт отправлен админу! Жди проверки и начисления награды.",
        'report_already': "⚠️ Ты уже отправлял отчёт по этому заданию!",
        'report_wait': "⚠️ Дождись проверки предыдущего отчёта!",
        'send_screenshot': "📸 Отправь скриншот выполнения задания (фото):",
        'report_approved': "✅ Твой отчёт одобрен! Начислено {amount} токенов.",
        'report_rejected': "❌ Твой отчёт отклонён. Награда не начислена.",
        'balance_header': "💰 Твой баланс{badge}: *{balance} токенов*",
        'balance_premium_until': "👑 Премиум активен до: *{date}*",
        'balance_topup_title': "🔄 *Способы пополнения:*",
        'balance_stars': "⭐️ *Telegram Stars* — мгновенно и автоматически",
        'balance_stars_rate': "   Курс: {rate} Stars за 1000 токенов{disc}",
        'balance_stars_min': "   Минимум: {min} токенов",
        'balance_disc': " (скидка премиум!)",
        'balance_rub': "💳 *Рубли* — через админа",
        'balance_rub_rate': "   Курс: {rate}₽ за 1000 токенов",
        'balance_rub_min': "   Минимум: {min}₽",
        'balance_premium': "👑 *Премиум-подписка:* {rub}₽ / {stars} Stars в месяц",
        'btn_topup_stars': "⭐️ Пополнить через Stars",
        'btn_topup_rub': "💳 Пополнить за рубли",
        'btn_buy_premium': "👑 Купить премиум ({stars} Stars)",
        'tasks_title': "📋 *Доступные задания:*\n\n",
        'tasks_line': "{mark}#{id} {type} — {reward} токенов\nОсталось мест: {left}\n\n",
        'btn_complete': "✅ Выполнить #{id}",
        'btn_report': "🚨 Пожаловаться #{id}",
        'create_title': "➕ Создание задания\n\nВыбери тип задания:",
        'type_subscribe': "📢 Подписка на канал",
        'type_reaction': "👍 Реакция на пост",
        'type_start_bot': "🤖 Запуск бота",
        'type_special': "⭐️ Особое задание",
        'type_names_subscribe': "📢 Подписка",
        'type_names_reaction': "👍 Реакция",
        'type_names_start_bot': "🤖 Запуск бота",
        'type_names_special': "⭐️ Особое",
        'link_prompt': "Отлично! Тип задания: *{type}*\n\nТеперь отправь ссылку (на канал/пост/бота):\nФорматы: https://t.me/username или @username",
        'link_invalid': "⚠️ Неправильный формат ссылки!\n\nИспользуй один из форматов:\n• https://t.me/username\n• @username\n• username",
        'link_accepted': "✅ Ссылка принята!\n\nТеперь укажи награду за одного исполнителя (минимум 100 токенов):\nНапример: 100",
        'num_invalid': "⚠️ Введи число! Например: 100",
        'reward_min': "⚠️ Минимальная награда — 100 токенов. Попробуй ещё раз:",
        'reward_set': "✅ Награда: {reward} токенов за одного исполнителя\n\nТеперь укажи общий бюджет задания:\nНапример: 500",
        'budget_invalid': "⚠️ Введи число! Например: 500",
        'budget_low': "⚠️ Бюджет должен быть больше или равен награде ({reward} токенов)!\nПопробуй ещё раз:",
        'budget_insufficient': "⚠️ Недостаточно токенов!\nТвой баланс: {balance} токенов\nНужно: {budget} токенов",
        'task_summary': "📋 Сводка задания:\n\nТип: {type}\nСсылка: {link}\nНаграда за исполнителя: {reward} токенов\nБюджет: {budget} токенов\nМакс. исполнителей: {max} чел.\nВернётся тебе: {rem} токенов\n\nПодтвердить создание?",
        'task_created': "✅ Задание успешно создано!\n\nТеперь его могут выполнять другие пользователи.",
        'task_cancelled': "❌ Создание задания отменено.",
        'ref_title': "👥 *Реферальная система*\n\nПриглашено друзей: {n}\nТы получаешь 10% от всех трат друга!\n\n*Твоя ссылка:*\n{link}\n\nОтправь эту ссылку друзьям!",
        'btn_copy_link': "📋 Скопировать ссылку",
        'support_title': "🛎 *Поддержка*\n\nОпиши свою проблему, и админ ответит тебе:",
        'support_sent': "✅ Сообщение отправлено админу! Жди ответа.",
        'history_title': "📜 *История транзакций (последние 20):*\n\n",
        'history_line': "{emoji} {sign}{amount} токенов — {desc}\n   🕐 {date}\n\n",
        'stats_title': "📊 *Твоя статистика{badge}*\n\n💰 Баланс: {balance} токенов\n✅ Выполнено заданий: {completed}\n➕ Создано заданий: {created}\n👥 Приглашено друзей: {refs}\n\n📈 Общий заработок: {earned} токенов\n📉 Общие траты: {spent} токенов\n📅 Регистрация: {reg}\n{prem}",
        'stats_prem': "👑 Премиум активен до: {date}",
        'top_title': "🏆 *ТОП ЗА {month}*\n\n",
        'top_line': "{medal} {name} — {n} токенов\n",
        'top_line_you': "{medal} *{name}* — {n} токенов ⭐️ *ТЫ*\n",
        'top_place': "\n📍 *Твоё место:* {p}\n💰 *Твой заработок:* {n} токенов\n",
        'top_prize': "\n🎁 *ТОП-3 получают премиум на 30 дней!*",
        'do_task_title': "📋 Задание #{id}\n\nТип: {type}\nНаграда: {reward} токенов\n\n⚠️ Важно: Не отписывайся в течение 48 часов, иначе получишь штраф -{penalty} токенов!\n\nВыполни задание и нажми 'Проверить выполнение':",
        'do_task_start_bot': "🤖 Задание #{id}\n\nТип: {type}\nНаграда: {reward} токенов\n\n1️⃣ Нажми '🔗 Перейти к боту' и запусти его\n2️⃣ Вернись сюда и нажми '✅ Подтвердить выполнение'\n3️⃣ Перешли сюда любое сообщение из этого бота\n\nБот проверит, что сообщение действительно из @{bot_username}, и начислит награду.",
        'do_task_special': "⭐️ Особое задание #{id}\n\nТип: {type}\nНаграда: {reward} токенов\n\n📝 Описание: {desc}\n\nВыполни задание и нажми 'Отправить отчёт', чтобы отправить скриншот админу.",
        'btn_go_task': "🔗 Перейти к боту",
        'btn_check': "✅ Подтвердить выполнение",
        'btn_send_report': "📸 Отправить отчёт",
        'err_not_subscribed': "⚠️ Ты не подписан на канал! Подпишись и попробуй снова.",
        'err_invalid_link': "⚠️ Неправильная ссылка!\n\nНужна ссылка на публичный канал вида:\nhttps://t.me/username_канала",
        'err_member_inaccessible': "⚠️ Бот не может проверить участников!\n\nВключена настройка «Скрыть список подписчиков».\nОтключи её в настройках канала:\nИзменить → Тип канала → Скрыть список подписчиков (ВЫКЛ)",
        'err_chat_not_found': "⚠️ Бот не может найти канал {name}!\n\nУбедись, что:\n1. Канал публичный\n2. Username указан правильно\n3. Бот добавлен в канал как администратор",
        'err_check': "⚠️ Ошибка проверки: {err}",
        'task_done': "✅ Задание выполнено!\n\nТебе начислено: {n} токенов",
        'penalty_msg': "⚠️ *Штраф за отписку!*\n\nТы отписался от канала раньше, чем через {hours} часов после выполнения задания #{id}.\nС твоего баланса списано *{amount} токенов*.",
        'premium_title': "👑 *Премиум-подписка*\n\n*Цена:* {stars} Telegram Stars\n\n*Преимущества:*\n• +{daily} токенов каждый день\n• Задания в первом ряду витрины\n• Создание заданий без выполнения 3 чужих\n• До {max} заданий в день\n• Бейдж 👑 в профиле\n• Приоритетная поддержка\n• Скидка 20% на пополнение\n\n⚠️ *Важно:* Подписка оформляется на {days} дней. Продление — ручное!\n\nНажми кнопку ниже для оплаты:",
        'btn_pay_premium': "💳 Оплатить {stars} Stars",
        'already_premium': "⚠️ У тебя уже активен премиум до {date}!",
        'topup_stars_title': "⭐️ *Пополнение через Telegram Stars*\n\nВведи количество токенов, которое хочешь получить.\n\n💰 Курс: *{rate} Stars* за 1000 токенов{disc}\n📏 Минимум: *{min} токенов*\n\n💡 Примеры:\n• 1000 токенов = {s1} Stars\n• 5000 токенов = {s5} Stars\n• 10000 токенов = {s10} Stars\n\nОтправь число токенов:",
        'topup_rub_title': "💳 *Пополнение за рубли через админа*\n\n💰 Курс: *{rate}₽* за 1000 токенов\n📏 Минимум: *{min}₽*\n\n💡 Как это работает:\n1. Ты отправляешь админу сумму и свой username\n2. Админ подтверждает оплату\n3. Токены начисляются на твой баланс\n\n⏱ Обычно начисление происходит в течение 1-24 часов.\n\nНажми кнопку ниже, чтобы написать админу:",
        'btn_contact_support': "🛎 Написать в поддержку",
        'support_rub_text': "🛎 Пополнение за рубли\n\nНапиши админу в таком формате:\n«Хочу пополнить на [количество] токенов. Мой username: @твой_username»\n\nАдмин ответит с реквизитами для оплаты.",
        'pay_confirm': "📋 *Подтверждение оплаты:*\n\nТокенов: *{tokens}*\nК оплате: *{stars} Telegram Stars*\n(эквивалент ~{rub}₽)\n\nНажми кнопку для оплаты:",
        'btn_pay': "✅ Оплатить {stars} Stars",
        'pay_success': "✅ *Баланс пополнен!*\n\nТебе начислено *{n} токенов*.",
        'premium_activated': "👑 *Премиум активирован!*\n\nСпасибо за покупку! Твой премиум активен до *{date}*.\n\nТеперь ты получаешь +{daily} токенов каждый день!",
        'cancel_exec': "❌ Выполнение задания отменено.",
        'report_dup': "⚠️ Ты уже жаловался на это задание!",
        'report_self': "⚠️ Нельзя жаловаться на своё задание!",
        'report_ok': "✅ Жалоба принята! ({n}/3 жалоб)",
        'report_hidden': "✅ Жалоба принята! Задание скрыто ({n}/3 жалоб).",
        'err_no_task': "❌ Задание не найдено!",
        'err_own': "⚠️ Нельзя выполнять своё собственное задание!",
        'err_done': "❌ Задание уже выполнено или неактивно!",
        'err_repeat': "⚠️ Ты уже выполнял это задание!",
        'err_banned': "⛔️ Ты заблокирован в боте!",
        'err_expired': "⚠️ Данные устарели, начни заново!",
        'err_no_reg': "⚠️ Сначала нажми /start чтобы зарегистрироваться!",
        'err_limit': "⚠️ Ты достиг лимита заданий на сегодня ({n}/{n})!",
        'err_need_3': "⚠️ Сначала выполни 3 чужих задания!\nВыполнено: {n}/3\n\n💡 Купи премиум, чтобы создавать задания сразу!",
        'err_no_tokens': "⚠️ Недостаточно токенов! Минимум 100 токенов для создания задания.",
        'refresh': "🔄 Обновить",
        'promo_title': "🎁 *Активация промокода*\n\nВведи промокод:",
        'promo_success': "✅ Промокод активирован!\n\nТебе начислено *{amount} токенов*.\nПромокод: {code}",
        'promo_invalid': "❌ Промокод не найден или недействителен.",
        'promo_used': "⚠️ Ты уже активировал этот промокод!",
        'promo_expired': "⚠️ Промокод исчерпан (все использования закончились).",
        'forward_request': "📩 *Подтверждение запуска бота*\n\nПерешли сюда **любое сообщение** из бота @{bot_username}.\n\nЭто нужно, чтобы подтвердить, что ты действительно запустил бота. Сообщение должно быть переслано (не скопировано!):",
        'forward_wrong_bot': "⚠️ Это сообщение не из бота @{expected}!\n\nПерешли сообщение именно из @{expected}.",
        'forward_not_forwarded': "⚠️ Это не пересланное сообщение!\n\nНажми на сообщение в боте @{bot_username} → «Переслать» → выбери этот чат.",
        'forward_unknown_source': "⚠️ Не удалось определить источник сообщения.\n\nУбедись, что пересылаешь сообщение из бота @{bot_username}.",
        'forward_success': "✅ Бот подтверждён! Задание выполнено.\n\nТебе начислено: {n} токенов",
        'my_tasks_title': "🗑 *Мои задания*\n\nНажми кнопку, чтобы удалить задание и вернуть неиспользованные токены:\n\n",
        'my_task_line': "#{id} {type} — {reward} токенов\nВыполнено: {done}/{max}\nВернётся при удалении: {refund} токенов\n",
        'task_deleted': "✅ Задание #{id} удалено!\n\nТебе возвращено: *{refund} токенов*",
        'task_already_done': "⚠️ Это задание уже полностью выполнено, удалять нечего.",
        'choose_lang': "🌐 *Выбери язык*\n\nНажми кнопку для смены языка:",
        'lang_changed': "✅ Язык изменён на *{lang_name}*!",
        'lang_ru': "🇷🇺 Русский",
        'lang_en': "🇬🇧 English",
        'lang_uk': "🇺🇦 Українська",
        'help_text': "ℹ️ *Как работает бот*\n\n📋 *Взять задание* — выполняй задания и получай токены\n➕ *Создать задание* — размести рекламу своего канала\n🗑 *Мои задания* — удали свои задания и верни токены\n💰 *Баланс* — пополняй через Telegram Stars или рубли\n👥 *Рефералы* — приглашай друзей и получай 10% от их трат\n🛎 *Поддержка* — вопросы к админу\n🎁 *Промокод* — активируй промокод и получи бонус\n\n👑 *Премиум (120 Stars/месяц):*\n• +600 токенов каждый день\n• Задания в первом ряду витрины\n• Создание заданий без выполнения 3 чужих\n• До 10 заданий в день\n• Бейдж 👑 и приоритетная поддержка\n• Скидка 20% на пополнение\n\n📌 *Правила:*\n• Минимальная награда: 100 токенов\n• Стартовый бонус: 300 токенов\n• Штраф за отписку: -200 токенов (через 48 часов)\n• Создать задание можно после выполнения 3 чужих (или с премиумом)\n\n📜 *Команды:*\n• /history — история транзакций\n• /stats — твоя статистика\n• /top — рейтинг за месяц (ТОП-3 получают премиум!)\n• /promo — активировать промокод\n• /lang — сменить язык",
        'subscribe_warning': "⚠️ *Важно для создателя задания:*\n\nЧтобы задание работало корректно, бот должен быть:\n1️⃣ Добавлен в канал как *администратор*\n2️⃣ Настройка «Скрыть список подписчиков» должна быть *ВЫКЛЮЧЕНА*\n\nЕсли эти условия не выполнены, задание выдаст ошибку при проверке.",
    },
    'en': {
        'welcome_new': "👋 Welcome, {name}!\n\n🎁 You got a starting bonus: *{bonus} tokens*!\nYour balance: *{balance} tokens*.\n\nThis is a mutual PR bot: complete tasks, earn tokens, and promote your channel!",
        'welcome_back': "Welcome back, {name}!\nYour balance: *{balance} tokens*.",
        'main_menu': "Main menu:",
        'btn_tasks': "📋 Take task",
        'btn_create': "➕ Create task",
        'btn_my_tasks': "🗑 My tasks",
        'btn_balance': "💰 Balance & top-up",
        'btn_top': "🏆 Monthly TOP",
        'btn_referrals': "👥 Referrals",
        'btn_support': "🛎 Support",
        'btn_lang': "🌐 Language",
        'btn_promo': "🎁 Promo code",
        'btn_back': "🔙 Back",
        'btn_menu': "🔙 To menu",
        'btn_cancel': "❌ Cancel",
        'btn_confirm': "✅ Confirm",
        'btn_delete': "🗑 Delete #{id}",
        'no_tasks': "📋 No tasks available right now. Try later!",
        'no_my_tasks': "📋 You have no active tasks.",
        'top_empty': "🏆 No one has earned tokens this month yet. Be the first! 🚀",
        'no_transactions': "📜 You have no transactions yet.",
        'report_sent': "✅ Report sent to admin! Wait for review and reward.",
        'report_already': "⚠️ You already submitted a report for this task!",
        'report_wait': "⚠️ Wait for previous report to be reviewed!",
        'send_screenshot': "📸 Send a screenshot of task completion (photo):",
        'report_approved': "✅ Your report is approved! {amount} tokens credited.",
        'report_rejected': "❌ Your report is rejected. No reward.",
        'balance_header': "💰 Your balance{badge}: *{balance} tokens*",
        'balance_premium_until': "👑 Premium active until: *{date}*",
        'balance_topup_title': "🔄 *Top-up methods:*",
        'balance_stars': "⭐️ *Telegram Stars* — instant and automatic",
        'balance_stars_rate': "   Rate: {rate} Stars per 1000 tokens{disc}",
        'balance_stars_min': "   Minimum: {min} tokens",
        'balance_disc': " (premium discount!)",
        'balance_rub': "💳 *Rubles* — via admin",
        'balance_rub_rate': "   Rate: {rate}₽ per 1000 tokens",
        'balance_rub_min': "   Minimum: {min}₽",
        'balance_premium': "👑 *Premium subscription:* {rub}₽ / {stars} Stars per month",
        'btn_topup_stars': "⭐️ Top up via Stars",
        'btn_topup_rub': "💳 Top up via rubles",
        'btn_buy_premium': "👑 Buy premium ({stars} Stars)",
        'tasks_title': "📋 *Available tasks:*\n\n",
        'tasks_line': "{mark}#{id} {type} — {reward} tokens\nRemaining spots: {left}\n\n",
        'btn_complete': "✅ Complete #{id}",
        'btn_report': "🚨 Report #{id}",
        'create_title': "➕ Create task\n\nChoose task type:",
        'type_subscribe': "📢 Channel subscription",
        'type_reaction': "👍 Post reaction",
        'type_start_bot': "🤖 Start bot",
        'type_special': "⭐️ Special task",
        'type_names_subscribe': "📢 Subscribe",
        'type_names_reaction': "👍 Reaction",
        'type_names_start_bot': "🤖 Start bot",
        'type_names_special': "⭐️ Special",
        'link_prompt': "Great! Task type: *{type}*\n\nNow send a link (to channel/post/bot):\nFormats: https://t.me/username or @username",
        'link_invalid': "⚠️ Invalid link format!\n\nUse one of these formats:\n• https://t.me/username\n• @username\n• username",
        'link_accepted': "✅ Link accepted!\n\nNow specify reward per executor (minimum 100 tokens):\nFor example: 100",
        'num_invalid': "⚠️ Enter a number! For example: 100",
        'reward_min': "⚠️ Minimum reward is 100 tokens. Try again:",
        'reward_set': "✅ Reward: {reward} tokens per executor\n\nNow specify total task budget:\nFor example: 500",
        'budget_invalid': "⚠️ Enter a number! For example: 500",
        'budget_low': "⚠️ Budget must be greater than or equal to reward ({reward} tokens)!\nTry again:",
        'budget_insufficient': "⚠️ Not enough tokens!\nYour balance: {balance} tokens\nRequired: {budget} tokens",
        'task_summary': "📋 Task summary:\n\nType: {type}\nLink: {link}\nReward per executor: {reward} tokens\nBudget: {budget} tokens\nMax executors: {max} people\nWill return to you: {rem} tokens\n\nConfirm creation?",
        'task_created': "✅ Task created successfully!\n\nNow others can complete it.",
        'task_cancelled': "❌ Task creation cancelled.",
        'ref_title': "👥 *Referral system*\n\nInvited friends: {n}\nYou get 10% of your friend's spending!\n\n*Your link:*\n{link}\n\nShare this link with friends!",
        'btn_copy_link': "📋 Copy link",
        'support_title': "🛎 *Support*\n\nDescribe your issue, and the admin will help you:",
        'support_sent': "✅ Message sent to admin! Wait for reply.",
        'history_title': "📜 *Transaction history (last 20):*\n\n",
        'history_line': "{emoji} {sign}{amount} tokens — {desc}\n   🕐 {date}\n\n",
        'stats_title': "📊 *Your statistics{badge}*\n\n💰 Balance: {balance} tokens\n✅ Tasks completed: {completed}\n➕ Tasks created: {created}\n👥 Friends invited: {refs}\n\n📈 Total earned: {earned} tokens\n📉 Total spent: {spent} tokens\n📅 Registered: {reg}\n{prem}",
        'stats_prem': "👑 Premium active until: {date}",
        'top_title': "🏆 *TOP FOR {month}*\n\n",
        'top_line': "{medal} {name} — {n} tokens\n",
        'top_line_you': "{medal} *{name}* — {n} tokens ⭐️ *YOU*\n",
        'top_place': "\n📍 *Your place:* {p}\n💰 *Your earnings:* {n} tokens\n",
        'top_prize': "\n🎁 *TOP-3 receive premium for 30 days!*",
        'do_task_title': "📋 Task #{id}\n\nType: {type}\nReward: {reward} tokens\n\n⚠️ Important: Do not unsubscribe within 48 hours, or you will be fined -{penalty} tokens!\n\nComplete the task and press 'Check completion':",
        'do_task_start_bot': "🤖 Task #{id}\n\nType: {type}\nReward: {reward} tokens\n\n1️⃣ Press '🔗 Go to bot' and start it\n2️⃣ Come back here and press '✅ Confirm completion'\n3️⃣ Forward any message from that bot here\n\nThe bot will verify the message is really from @{bot_username} and credit the reward.",
        'do_task_special': "⭐️ Special task #{id}\n\nType: {type}\nReward: {reward} tokens\n\n📝 Description: {desc}\n\nComplete the task and press 'Send report' to submit your screenshot.",
        'btn_go_task': "🔗 Go to bot",
        'btn_check': "✅ Confirm completion",
        'btn_send_report': "📸 Send report",
        'err_not_subscribed': "⚠️ You are not subscribed! Subscribe and try again.",
        'err_invalid_link': "⚠️ Invalid link!\n\nNeed a link to a public channel like:\nhttps://t.me/channel_username",
        'err_member_inaccessible': "⚠️ Bot cannot check members!\n\nChannel has 'Hide subscribers' enabled.\nDisable it in channel settings:\nEdit → Channel type → Hide subscribers (OFF)",
        'err_chat_not_found': "⚠️ Bot cannot find channel {name}!\n\nMake sure:\n1. Channel is public\n2. Username is correct\n3. Bot is added as admin",
        'err_check': "⚠️ Check error: {err}",
        'task_done': "✅ Task completed!\n\nYou received: {n} tokens",
        'penalty_msg': "⚠️ *Unsubscribe penalty!*\n\nYou unsubscribed before {hours} hours after completing task #{id}.\n{amount} tokens have been deducted from your balance.",
        'premium_title': "👑 *Premium subscription*\n\n*Price:* {stars} Telegram Stars\n\n*Benefits:*\n• +{daily} tokens every day\n• Tasks in first row\n• Create tasks without 3 completed\n• Up to {max} tasks per day\n• 👑 badge in profile\n• Priority support\n• 20% discount on top-up\n\n⚠️ *Important:* Subscription is for {days} days. Renewal is manual.\n\nPress button below to pay:",
        'btn_pay_premium': "💳 Pay {stars} Stars",
        'already_premium': "⚠️ You already have premium until {date}!",
        'topup_stars_title': "⭐️ *Top up via Telegram Stars*\n\nEnter the number of tokens you want to receive.\n\n💰 Rate: *{rate} Stars* per 1000 tokens{disc}\n📏 Minimum: *{min} tokens*\n\n💡 Examples:\n• 1000 tokens = {s1} Stars\n• 5000 tokens = {s5} Stars\n• 10000 tokens = {s10} Stars\n\nSend the number of tokens:",
        'topup_rub_title': "💳 *Top up via rubles through admin*\n\n💰 Rate: *{rate}₽* per 1000 tokens\n📏 Minimum: *{min}₽*\n\n💡 How it works:\n1. Send admin the amount and your username\n2. Admin confirms payment\n3. Tokens are added to your balance\n\n⏱ Usually takes 1-24 hours.\n\nPress button below to contact admin:",
        'btn_contact_support': "🛎 Contact support",
        'support_rub_text': "🛎 Top up via rubles\n\nWrite to admin in this format:\nI want to top up [amount] tokens. My username: @your_username\n\nAdmin will reply with payment details.",
        'pay_confirm': "📋 *Payment confirmation:*\n\nTokens: *{tokens}*\nTo pay: *{stars} Telegram Stars*\n(equivalent ~{rub}₽)\n\nPress button to pay:",
        'btn_pay': "✅ Pay {stars} Stars",
        'pay_success': "✅ *Balance topped up!*\n\nYou received *{n} tokens*.",
        'premium_activated': "👑 *Premium activated!*\n\nThank you for purchase! Your premium is active until *{date}*.\n\nNow you receive +{daily} tokens every day!",
        'cancel_exec': "❌ Task execution cancelled.",
        'report_dup': "⚠️ You already reported this task!",
        'report_self': "⚠️ Cannot report your own task!",
        'report_ok': "✅ Report accepted! ({n}/3 reports)",
        'report_hidden': "✅ Report accepted! Task hidden ({n}/3 reports).",
        'err_no_task': "❌ Task not found!",
        'err_own': "⚠️ Cannot complete your own task!",
        'err_done': "❌ Task already completed or inactive!",
        'err_repeat': "⚠️ You already completed this task!",
        'err_banned': "⛔️ You are banned!",
        'err_expired': "⚠️ Data expired, start over!",
        'err_no_reg': "⚠️ First press /start to register!",
        'err_limit': "⚠️ You reached the daily task limit ({n}/{n})!",
        'err_need_3': "⚠️ First complete 3 tasks from others!\nCompleted: {n}/3\n\n💡 Buy premium to create tasks immediately!",
        'err_no_tokens': "⚠️ Not enough tokens! Minimum 100 tokens to create a task.",
        'refresh': "🔄 Refresh",
        'promo_title': "🎁 *Promo code activation*\n\nEnter promo code:",
        'promo_success': "✅ Promo code activated!\n\nYou received *{amount} tokens*.\nCode: {code}",
        'promo_invalid': "❌ Promo code not found or invalid.",
        'promo_used': "⚠️ You already activated this promo code!",
        'promo_expired': "⚠️ Promo code is exhausted (all uses are taken).",
        'forward_request': "📩 *Bot launch confirmation*\n\nForward **any message** from bot @{bot_username} here.\n\nThis confirms you really started the bot. The message must be forwarded (not copied!):",
        'forward_wrong_bot': "⚠️ This message is not from bot @{expected}!\n\nForward a message specifically from @{expected}.",
        'forward_not_forwarded': "⚠️ This is not a forwarded message!\n\nTap the message in bot @{bot_username} → 'Forward' → choose this chat.",
        'forward_unknown_source': "⚠️ Could not determine message source.\n\nMake sure you forward a message from bot @{bot_username}.",
        'forward_success': "✅ Bot confirmed! Task completed.\n\nYou received: {n} tokens",
        'my_tasks_title': "🗑 *My tasks*\n\nPress a button to delete a task and get unused tokens back:\n\n",
        'my_task_line': "#{id} {type} — {reward} tokens\nCompleted: {done}/{max}\nRefund on delete: {refund} tokens\n",
        'task_deleted': "✅ Task #{id} deleted!\n\nYou received: *{refund} tokens*",
        'task_already_done': "⚠️ This task is already fully completed, nothing to delete.",
        'choose_lang': "🌐 *Choose language*\n\nTap a button to change language:",
        'lang_changed': "✅ Language changed to *{lang_name}*!",
        'lang_ru': "🇷🇺 Русский",
        'lang_en': "🇬🇧 English",
        'lang_uk': "🇺🇦 Українська",
        'help_text': "ℹ️ *How the bot works*\n\n📋 *Take task* — complete tasks and earn tokens\n➕ *Create task* — advertise your channel\n🗑 *My tasks* — delete your tasks and get tokens back\n💰 *Balance* — top up via Telegram Stars or rubles\n👥 *Referrals* — invite friends and get 10% of their spending\n🛎 *Support* — contact admin\n🎁 *Promo* — activate promo code for bonus\n\n👑 *Premium (120 Stars/month):*\n• +600 tokens every day\n• Tasks in first row\n• Create tasks without 3 completed\n• Up to 10 tasks per day\n• 👑 badge and priority support\n• 20% discount on top-up\n\n📌 *Rules:*\n• Min reward: 100 tokens\n• Starting bonus: 300 tokens\n• Unsubscribe penalty: -200 tokens (after 48 hours)\n• Create task after 3 completed (or with premium)\n\n📜 *Commands:*\n• /history — transaction history\n• /stats — your statistics\n• /top — monthly rating (TOP-3 get premium!)\n• /promo — activate promo code\n• /lang — change language",
        'subscribe_warning': "⚠️ *Important for task creator:*\n\nFor the task to work correctly, the bot must be:\n1️⃣ Added to the channel as an *administrator*\n2️⃣ The 'Hide subscribers' setting must be *DISABLED*\n\nIf these conditions are not met, the task will show an error during verification.",
    },
    'uk': {
        'welcome_new': "👋 Ласкаво просимо, {name}!\n\n🎁 Ти отримав стартовий бонус: *{bonus} токенів*!\nТвій баланс: *{balance} токенів*.\n\nЦе бот взаємного PR: виконуй завдання, заробляй токени та просувай свій канал!",
        'welcome_back': "З поверненням, {name}!\nТвій баланс: *{balance} токенів*.",
        'main_menu': "Головне меню:",
        'btn_tasks': "📋 Взяти завдання",
        'btn_create': "➕ Створити завдання",
        'btn_my_tasks': "🗑 Мої завдання",
        'btn_balance': "💰 Баланс і поповнення",
        'btn_top': "🏆 ТОП місяця",
        'btn_referrals': "👥 Реферали",
        'btn_support': "🛎 Підтримка",
        'btn_lang': "🌐 Мова",
        'btn_promo': "🎁 Промокод",
        'btn_back': "🔙 Назад",
        'btn_menu': "🔙 В меню",
        'btn_cancel': "❌ Скасувати",
        'btn_confirm': "✅ Підтвердити",
        'btn_delete': "🗑 Видалити #{id}",
        'no_tasks': "📋 Зараз немає доступних завдань. Спробуй пізніше!",
        'no_my_tasks': "📋 У тебе немає активних завдань.",
        'top_empty': "🏆 Цього місяця ще ніхто не заробив токенів. Стань першим! 🚀",
        'no_transactions': "📜 У тебе поки немає транзакцій.",
        'report_sent': "✅ Звіт надіслано адміну! Чекай на перевірку.",
        'report_already': "⚠️ Ти вже надсилав звіт по цьому завданню!",
        'report_wait': "⚠️ Дочекайся перевірки попереднього звіту!",
        'send_screenshot': "📸 Надішли скріншот виконання завдання (фото):",
        'report_approved': "✅ Твій звіт схвалено! Нараховано {amount} токенів.",
        'report_rejected': "❌ Твій звіт відхилено. Нагорода не нарахована.",
        'balance_header': "💰 Твій баланс{badge}: *{balance} токенів*",
        'balance_premium_until': "👑 Преміум активний до: *{date}*",
        'balance_topup_title': "🔄 *Способи поповнення:*",
        'balance_stars': "⭐️ *Telegram Stars* — миттєво та автоматично",
        'balance_stars_rate': "   Курс: {rate} Stars за 1000 токенів{disc}",
        'balance_stars_min': "   Мінімум: {min} токенів",
        'balance_disc': " (знижка преміум!)",
        'balance_rub': "💳 *Гривні* — через адміна",
        'balance_rub_rate': "   Курс: {rate}₽ за 1000 токенів",
        'balance_rub_min': "   Мінімум: {min}₽",
        'balance_premium': "👑 *Преміум-підписка:* {rub}₽ / {stars} Stars на місяць",
        'btn_topup_stars': "⭐️ Поповнити через Stars",
        'btn_topup_rub': "💳 Поповнити за гривні",
        'btn_buy_premium': "👑 Купити преміум ({stars} Stars)",
        'tasks_title': "📋 *Доступні завдання:*\n\n",
        'tasks_line': "{mark}#{id} {type} — {reward} токенів\nЗалишилось місць: {left}\n\n",
        'btn_complete': "✅ Виконати #{id}",
        'btn_report': "🚨 Поскаржитись #{id}",
        'create_title': "➕ Створення завдання\n\nОбери тип завдання:",
        'type_subscribe': "📢 Підписка на канал",
        'type_reaction': "👍 Реакція на пост",
        'type_start_bot': "🤖 Запуск бота",
        'type_special': "⭐️ Особливе завдання",
        'type_names_subscribe': "📢 Підписка",
        'type_names_reaction': "👍 Реакція",
        'type_names_start_bot': "🤖 Запуск бота",
        'type_names_special': "⭐️ Особливе",
        'link_prompt': "Чудово! Тип завдання: *{type}*\n\nТепер надішли посилання (на канал/пост/бота):\nФормати: https://t.me/username або @username",
        'link_invalid': "⚠️ Неправильний формат посилання!\n\nВикористовуй один із форматів:\n• https://t.me/username\n• @username\n• username",
        'link_accepted': "✅ Посилання прийнято!\n\nТепер вкажи нагороду за одного виконавця (мінімум 100 токенів):\nНаприклад: 100",
        'num_invalid': "⚠️ Введи число! Наприклад: 100",
        'reward_min': "⚠️ Мінімальна нагорода — 100 токенів. Спробуй ще раз:",
        'reward_set': "✅ Нагорода: {reward} токенів за одного виконавця\n\nТепер вкажи загальний бюджет завдання:\nНаприклад: 500",
        'budget_invalid': "⚠️ Введи число! Наприклад: 500",
        'budget_low': "⚠️ Бюджет повинен бути більшим або дорівнювати нагороді ({reward} токенів)!\nСпробуй ще раз:",
        'budget_insufficient': "⚠️ Недостатньо токенів!\nТвій баланс: {balance} токенів\nПотрібно: {budget} токенів",
        'task_summary': "📋 Зведення завдання:\n\nТип: {type}\nПосилання: {link}\nНагорода за виконавця: {reward} токенів\nБюджет: {budget} токенів\nМакс. виконавців: {max} осіб\nПовернеться тобі: {rem} токенів\n\nПідтвердити створення?",
        'task_created': "✅ Завдання успішно створено!\n\nТепер його можуть виконувати інші користувачі.",
        'task_cancelled': "❌ Створення завдання скасовано.",
        'ref_title': "👥 *Реферальна система*\n\nЗапрошено друзів: {n}\nТи отримуєш 10% від усіх витрат друга!\n\n*Твоє посилання:*\n{link}\n\nНадішли це посилання друзям!",
        'btn_copy_link': "📋 Скопіювати посилання",
        'support_title': "🛎 *Підтримка*\n\nОпиши свою проблему, і адмін відповість тобі:",
        'support_sent': "✅ Повідомлення надіслано адміну! Чекай на відповідь.",
        'history_title': "📜 *Історія транзакцій (останні 20):*\n\n",
        'history_line': "{emoji} {sign}{amount} токенів — {desc}\n   🕐 {date}\n\n",
        'stats_title': "📊 *Твоя статистика{badge}*\n\n💰 Баланс: {balance} токенів\n✅ Виконано завдань: {completed}\n➕ Створено завдань: {created}\n👥 Запрошено друзів: {refs}\n\n📈 Загальний заробіток: {earned} токенів\n📉 Загальні витрати: {spent} токенів\n📅 Реєстрація: {reg}\n{prem}",
        'stats_prem': "👑 Преміум активний до: {date}",
        'top_title': "🏆 *ТОП ЗА {month}*\n\n",
        'top_line': "{medal} {name} — {n} токенів\n",
        'top_line_you': "{medal} *{name}* — {n} токенів ⭐️ *ТИ*\n",
        'top_place': "\n📍 *Твоє місце:* {p}\n💰 *Твій заробіток:* {n} токенів\n",
        'top_prize': "\n🎁 *ТОП-3 отримують преміум на 30 днів!*",
        'do_task_title': "📋 Завдання #{id}\n\nТип: {type}\nНагорода: {reward} токенів\n\n⚠️ Важливо: Не відписуйся протягом 48 годин, інакше отримаєш штраф -{penalty} токенів!\n\nВиконай завдання та натисни 'Перевірити виконання':",
        'do_task_start_bot': "🤖 Завдання #{id}\n\nТип: {type}\nНагорода: {reward} токенів\n\n1️⃣ Натисни '🔗 Перейти до бота' і запусти його\n2️⃣ Повернись сюди і натисни '✅ Підтвердити виконання'\n3️⃣ Перешли сюди будь-яке повідомлення з цього бота\n\nБот перевірить, що повідомлення дійсно з @{bot_username}, і нарахує нагороду.",
        'do_task_special': "⭐️ Особливе завдання #{id}\n\nТип: {type}\nНагорода: {reward} токенів\n\n📝 Опис: {desc}\n\nВиконай завдання та натисни 'Надіслати звіт', щоб надіслати скріншот адміну.",
        'btn_go_task': "🔗 Перейти до бота",
        'btn_check': "✅ Підтвердити виконання",
        'btn_send_report': "📸 Надіслати звіт",
        'err_not_subscribed': "⚠️ Ти не підписаний на канал! Підпишись і спробуй знову.",
        'err_invalid_link': "⚠️ Неправильне посилання!\n\nПотрібне посилання на публічний канал:\nhttps://t.me/username_каналу",
        'err_member_inaccessible': "⚠️ Бот не може перевірити учасників!\n\nУвімкнено налаштування «Приховати список підписників».\nВимкни його в налаштуваннях каналу.",
        'err_chat_not_found': "⚠️ Бот не може знайти канал {name}!\n\nПереконайся, що:\n1. Канал публічний\n2. Username вказано правильно\n3. Бот доданий в канал як адміністратор",
        'err_check': "⚠️ Помилка перевірки: {err}",
        'task_done': "✅ Завдання виконано!\n\nТобі нараховано: {n} токенів",
        'penalty_msg': "⚠️ *Штраф за відписку!*\n\nТи відписався від каналу раніше, ніж через {hours} годин після виконання завдання #{id}.\nЗ твого балансу списано *{amount} токенів*.",
        'premium_title': "👑 *Преміум-підписка*\n\n*Ціна:* {stars} Telegram Stars\n\n*Переваги:*\n• +{daily} токенів щодня\n• Завдання в першому ряду\n• Створення завдань без виконання 3 чужих\n• До {max} завдань на день\n• Бейдж 👑 в профілі\n• Пріоритетна підтримка\n• Знижка 20% на поповнення\n\n⚠️ *Важливо:* Підписка оформлюється на {days} днів.\n\nНатисни кнопку нижче для оплати:",
        'btn_pay_premium': "💳 Оплатити {stars} Stars",
        'already_premium': "⚠️ У тебе вже активний преміум до {date}!",
        'topup_stars_title': "⭐️ *Поповнення через Telegram Stars*\n\nВведи кількість токенів, яку хочеш отримати.\n\n💰 Курс: *{rate} Stars* за 1000 токенів{disc}\n📏 Мінімум: *{min} токенів*\n\n💡 Приклади:\n• 1000 токенів = {s1} Stars\n• 5000 токенів = {s5} Stars\n• 10000 токенів = {s10} Stars\n\nНадішли число токенів:",
        'topup_rub_title': "💳 *Поповнення за гривні через адміна*\n\n💰 Курс: *{rate}₽* за 1000 токенів\n📏 Мінімум: *{min}₽*\n\n💡 Як це працює:\n1. Ти надсилаєш адміну суму та свій username\n2. Адмін підтверджує оплату\n3. Токени нараховуються на твій баланс\n\n⏱ Зазвичай триває 1-24 години.\n\nНатисни кнопку нижче, щоб написати адміну:",
        'btn_contact_support': "🛎 Написати в підтримку",
        'support_rub_text': "🛎 Поповнення за гривні\n\nНапиши адміну в такому форматі:\n«Хочу поповнити на [кількість] токенів. Мій username: @твій_username»\n\nАдмін відповість з реквізитами для оплати.",
        'pay_confirm': "📋 *Підтвердження оплати:*\n\nТокенів: *{tokens}*\nДо оплати: *{stars} Telegram Stars*\n(еквівалент ~{rub}₽)\n\nНатисни кнопку для оплати:",
        'btn_pay': "✅ Оплатити {stars} Stars",
        'pay_success': "✅ *Баланс поповнено!*\n\nТобі нараховано *{n} токенів*.",
        'premium_activated': "👑 *Преміум активовано!*\n\nДякуємо за покупку! Твій преміум активний до *{date}*.\n\nТепер ти отримуєш +{daily} токенів щодня!",
        'cancel_exec': "❌ Виконання завдання скасовано.",
        'report_dup': "⚠️ Ти вже скаржився на це завдання!",
        'report_self': "⚠️ Не можна скаржитись на своє завдання!",
        'report_ok': "✅ Скаргу прийнято! ({n}/3 скарг)",
        'report_hidden': "✅ Скаргу прийнято! Завдання приховано ({n}/3 скарг).",
        'err_no_task': "❌ Завдання не знайдено!",
        'err_own': "⚠️ Не можна виконувати своє власне завдання!",
        'err_done': "❌ Завдання вже виконано або неактивне!",
        'err_repeat': "⚠️ Ти вже виконував це завдання!",
        'err_banned': "⛔️ Ти заблокований у боті!",
        'err_expired': "⚠️ Дані застаріли, почни заново!",
        'err_no_reg': "⚠️ Спочатку натисни /start щоб зареєструватися!",
        'err_limit': "⚠️ Ти досяг ліміту завдань на сьогодні ({n}/{n})!",
        'err_need_3': "⚠️ Спочатку виконай 3 чужі завдання!\nВиконано: {n}/3\n\n💡 Купи преміум, щоб створювати завдання одразу!",
        'err_no_tokens': "⚠️ Недостатньо токенів! Мінімум 100 токенів для створення завдання.",
        'refresh': "🔄 Оновити",
        'promo_title': "🎁 *Активація промокоду*\n\nВведи промокод:",
        'promo_success': "✅ Промокод активовано!\n\nТобі нараховано *{amount} токенів*.\nКод: {code}",
        'promo_invalid': "❌ Промокод не знайдено або недійсний.",
        'promo_used': "⚠️ Ти вже активував цей промокод!",
        'promo_expired': "⚠️ Промокод вичерпано (всі використання закінчилися).",
        'forward_request': "📩 *Підтвердження запуску бота*\n\nПерешли сюди **будь-яке повідомлення** з бота @{bot_username}.\n\nЦе потрібно, щоб підтвердити, що ти дійсно запустив бота. Повідомлення має бути переслане (не скопійоване!):",
        'forward_wrong_bot': "⚠️ Це повідомлення не з бота @{expected}!\n\nПерешли повідомлення саме з @{expected}.",
        'forward_not_forwarded': "⚠️ Це не переслане повідомлення!\n\nНатисни на повідомлення в боті @{bot_username} → «Переслати» → обери цей чат.",
        'forward_unknown_source': "⚠️ Не вдалося визначити джерело повідомлення.\n\nПереконайся, що пересилаєш повідомлення з бота @{bot_username}.",
        'forward_success': "✅ Бот підтверджено! Завдання виконано.\n\nТобі нараховано: {n} токенів",
        'my_tasks_title': "🗑 *Мої завдання*\n\nНатисни кнопку, щоб видалити завдання та повернути невикористані токени:\n\n",
        'my_task_line': "#{id} {type} — {reward} токенів\nВиконано: {done}/{max}\nПовернеться при видаленні: {refund} токенів\n",
        'task_deleted': "✅ Завдання #{id} видалено!\n\nТобі повернуто: *{refund} токенів*",
        'task_already_done': "⚠️ Це завдання вже повністю виконано, видаляти нічого.",
        'choose_lang': "🌐 *Обери мову*\n\nНатисни кнопку для зміни мови:",
        'lang_changed': "✅ Мову змінено на *{lang_name}*!",
        'lang_ru': "🇷🇺 Русский",
        'lang_en': "🇬🇧 English",
        'lang_uk': "🇺🇦 Українська",
        'help_text': "ℹ️ *Як працює бот*\n\n📋 *Взяти завдання* — виконуй завдання та отримуй токени\n➕ *Створити завдання* — розмісти рекламу свого каналу\n🗑 *Мої завдання* — видали свої завдання та отримай токени назад\n💰 *Баланс* — поповнюй через Telegram Stars або гривні\n👥 *Реферали* — запрошуй друзів і отримуй 10% від їхніх витрат\n🛎 *Підтримка* — питання до адміна\n🎁 *Промокод* — активуй промокод і отримай бонус\n\n👑 *Преміум (120 Stars/місяць):*\n• +600 токенів щодня\n• Завдання в першому ряду\n• Створення завдань без виконання 3 чужих\n• До 10 завдань на день\n• Бейдж 👑 і пріоритетна підтримка\n• Знижка 20% на поповнення\n\n📌 *Правила:*\n• Мінімальна нагорода: 100 токенів\n• Стартовий бонус: 300 токенів\n• Штраф за відписку: -200 токенів (через 48 годин)\n• Створити завдання можна після виконання 3 чужих (або з преміумом)\n\n📜 *Команди:*\n• /history — історія транзакцій\n• /stats — твоя статистика\n• /top — рейтинг за місяць (ТОП-3 отримують преміум!)\n• /promo — активувати промокод\n• /lang — змінити мову",
        'subscribe_warning': "⚠️ *Важливо для творця завдання:*\n\nЩоб завдання працювало коректно, бот повинен бути:\n1️⃣ Доданий у канал як *адміністратор*\n2️⃣ Налаштування «Приховати список підписників» повинно бути *ВИМКНЕНО*\n\nЯкщо ці умови не виконані, завдання видасть помилку під час перевірки.",
    }
}

DEFAULT_LANG = 'ru'

def get_text(lang: str, key: str, **kwargs) -> str:
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANG
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT language_code FROM users WHERE telegram_id = ?', (user_id,))
        user = await cursor.fetchone()
        if user and user[0]:
            return user[0]
    return DEFAULT_LANG


async def set_user_lang(user_id: int, lang: str):
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANG
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('UPDATE users SET language_code = ? WHERE telegram_id = ?', (lang, user_id))
        await db.commit()


def extract_bot_username(link: str) -> str:
    username = link.replace("https://t.me/", "").replace("http://t.me/", "").strip()
    if '/' in username:
        username = username.split('/')[0]
    if username.startswith('@'):
        username = username[1:]
    return username.lower()


# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
START_BONUS = 300
PREMIUM_PRICE_STARS = 120
PREMIUM_PRICE_RUB = 199
PREMIUM_DURATION_DAYS = 30
DAILY_PREMIUM_BONUS = 600
NORMAL_TASKS_PER_DAY = 3
PREMIUM_TASKS_PER_DAY = 10
STARS_PER_1000_TOKENS = 10
STARS_PER_1000_TOKENS_PREMIUM = 8
RUB_PER_1000_TOKENS = 15
MIN_TOKENS_PURCHASE = 100
MIN_STARS_PURCHASE = 1
MIN_RUB_PURCHASE = 15
UNSUBSCRIBE_PENALTY = 200
PENALTY_HOURS = 48

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)
scheduler = AsyncIOScheduler()


# --- FSM СОСТОЯНИЯ ---
class CreateTaskStates(StatesGroup):
    choosing_type = State()
    entering_link = State()
    entering_reward = State()
    entering_budget = State()
    confirming = State()

class SupportStates(StatesGroup):
    waiting_message = State()

class PromoStates(StatesGroup):
    waiting_code = State()

class AdminStates(StatesGroup):
    mailing_message = State()
    ban_user = State()
    unban_user = State()
    create_promo = State()
    create_promo_amount = State()
    create_promo_uses = State()
    delete_promo = State()
    add_tokens_username = State()
    add_tokens_amount = State()
    add_premium_username = State()
    add_premium_days = State()
    replying_to_user = State()
    write_to_user_search = State()
    write_to_user_message = State()
    special_task_description = State()
    special_task_reward = State()
    entering_budget = State()
    delete_task_id = State()

class PayTokensStates(StatesGroup):
    entering_amount = State()

class ReportStates(StatesGroup):
    waiting_screenshot = State()

class ConfirmBotStates(StatesGroup):
    waiting_forward = State()


# --- БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                balance INTEGER DEFAULT 0,
                referrer_id INTEGER,
                tasks_completed INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                premium_expires_at TIMESTAMP,
                last_daily_bonus TIMESTAMP,
                tasks_today_count INTEGER DEFAULT 0,
                last_task_date TEXT,
                language_code TEXT DEFAULT 'ru',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                task_type TEXT,
                link TEXT,
                reward INTEGER,
                budget INTEGER,
                max_executors INTEGER,
                completed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                amount INTEGER,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS task_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                executor_id INTEGER,
                completed_at REAL,
                penalty_checked INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS premium_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount_stars INTEGER,
                duration_days INTEGER,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS task_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                reporter_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS special_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                user_id INTEGER,
                screenshot_file_id TEXT,
                caption TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            await db.execute('ALTER TABLE task_executions ADD COLUMN penalty_checked INTEGER DEFAULT 0')
        except:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN language_code TEXT DEFAULT 'ru'")
        except:
            pass
        try:
            await db.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
        except:
            pass
        await db.commit()


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def escape_md(text: str) -> str:
    if not text:
        return ""
    return str(text).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('>', '\\>')


async def get_or_create_user(telegram_id: int, username: str, referrer_id: int = None, language_code: str = 'ru'):
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = await cursor.fetchone()
        if not user:
            await db.execute(
                'INSERT INTO users (telegram_id, username, balance, referrer_id, language_code) VALUES (?, ?, ?, ?, ?)',
                (telegram_id, username, START_BONUS, referrer_id, language_code)
            )
            await db.execute(
                'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                (telegram_id, START_BONUS, 'bonus', 'Стартовый бонус')
            )
            await db.commit()
            return True, START_BONUS, False
        return False, user[3], bool(user[7])


async def check_and_give_daily_bonus(telegram_id: int):
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'SELECT is_premium, premium_expires_at, last_daily_bonus FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )
        user = await cursor.fetchone()
        if not user:
            return
        is_premium, premium_expires_at, last_daily_bonus = user
        if not is_premium:
            return
        if premium_expires_at and datetime.fromisoformat(premium_expires_at) < datetime.now():
            await db.execute('UPDATE users SET is_premium = 0 WHERE telegram_id = ?', (telegram_id,))
            await db.commit()
            return
        if last_daily_bonus:
            last_bonus = datetime.fromisoformat(last_daily_bonus)
            if datetime.now() - last_bonus < timedelta(hours=24):
                return
        await db.execute(
            'UPDATE users SET balance = balance + ?, last_daily_bonus = ? WHERE telegram_id = ?',
            (DAILY_PREMIUM_BONUS, datetime.now().isoformat(), telegram_id)
        )
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (telegram_id, DAILY_PREMIUM_BONUS, 'premium_daily', 'Ежедневный бонус премиум')
        )
        await db.commit()


async def check_daily_task_limit(telegram_id: int) -> tuple:
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'SELECT is_premium, premium_expires_at, tasks_today_count, last_task_date FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )
        user = await cursor.fetchone()
        if not user:
            return False, 0
        is_premium, premium_expires_at, tasks_today_count, last_task_date = user
        is_premium_active = False
        if is_premium and premium_expires_at:
            if datetime.fromisoformat(premium_expires_at) > datetime.now():
                is_premium_active = True
        limit = PREMIUM_TASKS_PER_DAY if is_premium_active else NORMAL_TASKS_PER_DAY
        today = datetime.now().date().isoformat()
        if last_task_date != today:
            await db.execute(
                'UPDATE users SET tasks_today_count = 0, last_task_date = ? WHERE telegram_id = ?',
                (today, telegram_id)
            )
            await db.commit()
            tasks_today_count = 0
        if tasks_today_count >= limit:
            return False, limit
        return True, limit


async def increment_daily_task_count(telegram_id: int):
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute(
            'UPDATE users SET tasks_today_count = tasks_today_count + 1 WHERE telegram_id = ?',
            (telegram_id,)
        )
        await db.commit()


def calculate_stars_for_tokens(tokens: int, is_premium: bool) -> int:
    price_per_1000 = STARS_PER_1000_TOKENS_PREMIUM if is_premium else STARS_PER_1000_TOKENS
    stars = math.ceil(tokens / 1000 * price_per_1000)
    return max(stars, MIN_STARS_PURCHASE)


def calculate_rub_for_tokens(tokens: int) -> int:
    rub = math.ceil(tokens / 1000 * RUB_PER_1000_TOKENS)
    return max(rub, MIN_RUB_PURCHASE)


# --- ПЛАНИРОВЩИК ШТРАФОВ ---
async def check_unsubscribe_penalty():
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT te.task_id, te.executor_id, te.completed_at, t.link, t.task_type
            FROM task_executions te
            JOIN tasks t ON te.task_id = t.id
            WHERE te.penalty_checked = 0
            AND (strftime('%s', 'now') - te.completed_at) >= ?
        ''', (PENALTY_HOURS * 3600,))
        executions = await cursor.fetchall()
        for task_id, executor_id, completed_at, link, task_type in executions:
            if task_type != 'subscribe':
                await db.execute(
                    'UPDATE task_executions SET penalty_checked = 1 WHERE task_id = ? AND executor_id = ?',
                    (task_id, executor_id)
                )
                continue
            try:
                channel_username = link.replace("https://t.me/", "").replace("http://t.me/", "").strip()
                if '/' in channel_username:
                    channel_username = channel_username.split('/')[0]
                if not channel_username.startswith('@'):
                    channel_username = f"@{channel_username}"
                member = await bot.get_chat_member(channel_username, executor_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    await db.execute(
                        'UPDATE users SET balance = balance - ? WHERE telegram_id = ?',
                        (UNSUBSCRIBE_PENALTY, executor_id)
                    )
                    await db.execute(
                        'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                        (executor_id, -UNSUBSCRIBE_PENALTY, 'unsubscribe_penalty', f'Штраф за отписку от задания #{task_id}')
                    )
                    user_lang = await get_user_lang(executor_id)
                    try:
                        await bot.send_message(
                            executor_id,
                            get_text(user_lang, 'penalty_msg', hours=PENALTY_HOURS, id=task_id, amount=UNSUBSCRIBE_PENALTY),
                            parse_mode="Markdown"
                        )
                    except:
                        pass
                    logger.warning(f"Penalty charged to user {executor_id} for task #{task_id}")
                await db.execute(
                    'UPDATE task_executions SET penalty_checked = 1 WHERE task_id = ? AND executor_id = ?',
                    (task_id, executor_id)
                )
            except Exception as e:
                logger.error(f"Error checking unsubscribe for user {executor_id}: {e}")
        await db.commit()


async def start_scheduler():
    scheduler.add_job(check_unsubscribe_penalty, 'interval', minutes=30)
    scheduler.start()
    print("⏰ Планировщик проверки отписки запущен (каждые 30 минут)")


# --- ТОП ПОЛЬЗОВАТЕЛЕЙ ЗА МЕСЯЦ ---
async def calculate_monthly_top():
    now = datetime.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_prev_month = first_day_this_month - timedelta(seconds=1)
    first_day_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT u.telegram_id, u.username, SUM(t.amount) as total_earned
            FROM users u
            JOIN transactions t ON u.telegram_id = t.user_id
            WHERE t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
            AND t.amount > 0
            AND t.created_at >= ? AND t.created_at <= ?
            AND u.is_banned = 0
            AND u.telegram_id != ?
            GROUP BY u.telegram_id
            ORDER BY total_earned DESC
            LIMIT 3
        ''', (first_day_prev_month.isoformat(), last_day_prev_month.isoformat(), ADMIN_ID))
        top_users = await cursor.fetchall()
    if not top_users:
        return
    prizes = ["🥇 1 МЕСТО", "🥈 2 МЕСТО", "🥉 3 МЕСТО"]
    winners_text = f"🏆 *ТОП ПОЛЬЗОВАТЕЛЕЙ ЗА {last_day_prev_month.strftime('%B %Y').upper()}*\n\n"
    for position, (telegram_id, username, total_earned) in enumerate(top_users):
        username_display = f"@{escape_md(username)}" if username else f"ID {telegram_id}"
        async with aiosqlite.connect('bot_database.db') as db:
            cursor = await db.execute(
                'SELECT is_premium, premium_expires_at FROM users WHERE telegram_id = ?',
                (telegram_id,)
            )
            user = await cursor.fetchone()
            if user and user[0] and user[1]:
                current_expires = datetime.fromisoformat(user[1])
                new_expires = (current_expires if current_expires > now else now) + timedelta(days=30)
            else:
                new_expires = now + timedelta(days=30)
            await db.execute(
                'UPDATE users SET is_premium = 1, premium_expires_at = ? WHERE telegram_id = ?',
                (new_expires.isoformat(), telegram_id)
            )
            await db.execute(
                'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                (telegram_id, 0, 'monthly_top_prize', f'Награда за {prizes[position]} в ТОП за месяц')
            )
            await db.commit()
        expires_str = escape_md(new_expires.strftime('%d.%m.%Y'))
        winners_text += f"{prizes[position]}: {username_display}\n   💰 Заработано: {total_earned} токенов\n   👑 Премиум до: {expires_str}\n\n"
        try:
            await bot.send_message(
                telegram_id,
                f"🎉 *Поздравляем!*\n\n"
                f"Ты занял *{prizes[position]}* в рейтинге за {last_day_prev_month.strftime('%B %Y')}!\n"
                f"Заработано: {total_earned} токенов\n\n"
                f"👑 Тебе начислен *премиум на 30 дней* (до {expires_str})!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {telegram_id}: {e}")
    await bot.send_message(ADMIN_ID, f"🏆 *Итоги месяца!*\n\n{winners_text}", parse_mode="Markdown")


async def start_monthly_top_scheduler():
    now = datetime.now()
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    scheduler.add_job(calculate_monthly_top, 'date', run_date=next_month, id='monthly_top')
    print(f"⏰ Автоматический подсчёт топа запланирован на {next_month.strftime('%d.%m.%Y %H:%M')}")


# --- КЛАВИАТУРЫ ---
def get_main_keyboard(is_premium: bool = False, lang: str = 'ru'):
    premium_badge = " 👑" if is_premium else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_tasks') + premium_badge, callback_data="view_tasks")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_create'), callback_data="create_task")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_my_tasks'), callback_data="my_tasks")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_balance'), callback_data="balance")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_promo'), callback_data="show_promo")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_top'), callback_data="show_top")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_referrals'), callback_data="referrals")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_support'), callback_data="support")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_lang'), callback_data="show_lang_menu")],
    ])
    return kb


# --- ОБРАБОТЧИКИ КОМАНД ---
@router.message(CommandStart())
async def cmd_start(message: Message):
    referrer_id = None
    if message.text and message.text.startswith('/start?ref='):
        try:
            referrer_id = int(message.text.split('=')[1])
        except ValueError:
            pass
    tg_lang = (message.from_user.language_code or 'ru').split('-')[0]
    if tg_lang not in TRANSLATIONS:
        tg_lang = 'ru'
    is_new, balance, was_premium = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "NoUsername",
        referrer_id=referrer_id,
        language_code=tg_lang
    )
    await check_and_give_daily_bonus(message.from_user.id)
    user_lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT balance, is_premium FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        balance = user[0]
        is_premium = bool(user[1])
    if is_new:
        text = get_text(user_lang, 'welcome_new', name=message.from_user.first_name, bonus=START_BONUS, balance=balance)
    else:
        text = get_text(user_lang, 'welcome_back', name=message.from_user.first_name, balance=balance)
    await message.answer(text, reply_markup=get_main_keyboard(is_premium, user_lang), parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(get_text(lang, 'help_text'), parse_mode="Markdown")


@router.message(Command("lang"))
async def cmd_lang(message: Message):
    lang = await get_user_lang(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'lang_ru'), callback_data="set_lang:ru")],
        [InlineKeyboardButton(text=get_text(lang, 'lang_en'), callback_data="set_lang:en")],
        [InlineKeyboardButton(text=get_text(lang, 'lang_uk'), callback_data="set_lang:uk")],
    ])
    await message.answer(get_text(lang, 'choose_lang'), reply_markup=kb, parse_mode="Markdown")


@router.message(Command("promo"))
async def cmd_promo(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(get_text(lang, 'promo_title'), parse_mode="Markdown")
    await state.set_state(PromoStates.waiting_code)


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT balance, is_premium, premium_expires_at FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        balance = user[0] if user else 0
        is_premium = bool(user[1]) if user else False
        premium_expires = user[2] if user else None
    premium_badge = " 👑" if is_premium else ""
    premium_info = ""
    if is_premium and premium_expires:
        expires = datetime.fromisoformat(premium_expires)
        premium_info = get_text(lang, 'balance_premium_until', date=escape_md(expires.strftime('%d.%m.%Y %H:%M')))
    stars_price = STARS_PER_1000_TOKENS_PREMIUM if is_premium else STARS_PER_1000_TOKENS
    disc = get_text(lang, 'balance_disc') if is_premium else ""
    text = (
        f"{get_text(lang, 'balance_header', badge=premium_badge, balance=balance)}\n"
        f"{premium_info}\n\n"
        f"{get_text(lang, 'balance_topup_title')}\n"
        f"{get_text(lang, 'balance_stars')}\n"
        f"{get_text(lang, 'balance_stars_rate', rate=stars_price, disc=disc)}\n"
        f"{get_text(lang, 'balance_stars_min', min=MIN_TOKENS_PURCHASE)}\n\n"
        f"{get_text(lang, 'balance_rub')}\n"
        f"{get_text(lang, 'balance_rub_rate', rate=RUB_PER_1000_TOKENS)}\n"
        f"{get_text(lang, 'balance_rub_min', min=MIN_RUB_PURCHASE)}\n\n"
        f"{get_text(lang, 'balance_premium', rub=PREMIUM_PRICE_RUB, stars=PREMIUM_PRICE_STARS)}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_topup_stars'), callback_data="pay_tokens_stars")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_topup_rub'), callback_data="pay_tokens_rub")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_buy_premium', stars=PREMIUM_PRICE_STARS), callback_data="buy_premium")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_menu'), callback_data="start_menu")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT t.id, t.task_type, t.link, t.reward, t.max_executors, t.completed_count, u.is_premium
            FROM tasks t
            LEFT JOIN users u ON t.creator_id = u.telegram_id
            WHERE t.status = 'active'
              AND t.completed_count < t.max_executors
              AND t.creator_id != ?
              AND NOT EXISTS (
                  SELECT 1 FROM task_executions te
                  WHERE te.task_id = t.id AND te.executor_id = ?
              )
            ORDER BY u.is_premium DESC, t.created_at DESC
            LIMIT 20
        ''', (message.from_user.id, message.from_user.id))
        tasks = await cursor.fetchall()
    if not tasks:
        await message.answer(get_text(lang, 'no_tasks'))
        return
    type_map = {
        "subscribe": get_text(lang, 'type_names_subscribe'),
        "reaction": get_text(lang, 'type_names_reaction'),
        "start_bot": get_text(lang, 'type_names_start_bot'),
        "special": get_text(lang, 'type_names_special'),
    }
    text = get_text(lang, 'tasks_title')
    kb_buttons = []
    for task in tasks:
        task_id, task_type, link, reward, max_exec, completed, is_premium = task
        remaining = max_exec - completed
        mark = "👑 " if is_premium else ""
        text += get_text(lang, 'tasks_line', mark=mark, id=task_id, type=type_map.get(task_type, task_type), reward=reward, left=remaining)
        kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_complete', id=task_id), callback_data=f"do_task:{task_id}")])
        kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_report', id=task_id), callback_data=f"report_task:{task_id}")])
    kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_menu'), callback_data="start_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'SELECT tasks_completed, balance, is_premium, premium_expires_at FROM users WHERE telegram_id = ?',
            (message.from_user.id,)
        )
        user = await cursor.fetchone()
        if not user:
            await message.answer(get_text(lang, 'err_no_reg'))
            return
        tasks_completed, balance, is_premium, premium_expires = user
        is_premium_active = False
        if is_premium and premium_expires:
            if datetime.fromisoformat(premium_expires) > datetime.now():
                is_premium_active = True
        can_create, limit = await check_daily_task_limit(message.from_user.id)
        if not can_create:
            await message.answer(get_text(lang, 'err_limit', n=limit))
            return
        if not is_premium_active and tasks_completed < 3:
            await message.answer(get_text(lang, 'err_need_3', n=tasks_completed))
            return
        if balance < 100:
            await message.answer(get_text(lang, 'err_no_tokens'))
            return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'type_subscribe'), callback_data="task_type:subscribe")],
        [InlineKeyboardButton(text=get_text(lang, 'type_reaction'), callback_data="task_type:reaction")],
        [InlineKeyboardButton(text=get_text(lang, 'type_start_bot'), callback_data="task_type:start_bot")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task")]
    ])
    await message.answer(get_text(lang, 'create_title'), reply_markup=kb)
    await state.set_state(CreateTaskStates.choosing_type)


@router.message(Command("ref"))
async def cmd_ref(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (message.from_user.id,))
        ref_count = (await cursor.fetchone())[0]
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref={message.from_user.id}"
    safe_link = escape_md(referral_link)
    text = get_text(lang, 'ref_title', n=ref_count, link=safe_link)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_copy_link'), url=referral_link)],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(get_text(lang, 'support_title'), parse_mode="Markdown")
    await state.set_state(SupportStates.waiting_message)


@router.message(Command("history"))
async def cmd_history(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT amount, type, description, created_at FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 20
        ''', (message.from_user.id,))
        transactions = await cursor.fetchall()
    if not transactions:
        await message.answer(get_text(lang, 'no_transactions'))
        return
    emoji_map = {
        'bonus': '🎁', 'task_complete': '✅', 'task_create': '➕', 'task_remainder': '↩️',
        'referral_bonus': '👥', 'premium_daily': '👑', 'stars_purchase': '⭐️',
        'admin_add': '🛠', 'unsubscribe_penalty': '⚠️', 'monthly_top_prize': '🏆',
        'special_task_approved': '⭐️', 'promo_activation': '🎁', 'task_delete_refund': '🗑',
    }
    text = get_text(lang, 'history_title')
    for amount, type, description, created_at in transactions:
        sign = "+" if amount > 0 else ""
        emoji = emoji_map.get(type, '💰')
        safe_description = escape_md(description) if description else "—"
        safe_created = escape_md(str(created_at)) if created_at else "—"
        text += get_text(lang, 'history_line', emoji=emoji, sign=sign, amount=amount, desc=safe_description, date=safe_created)
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT balance, tasks_completed, is_premium, premium_expires_at, created_at FROM users WHERE telegram_id = ?
        ''', (message.from_user.id,))
        user = await cursor.fetchone()
        if not user:
            await message.answer(get_text(lang, 'err_no_reg'))
            return
        balance, tasks_completed, is_premium, premium_expires, created_at = user
        tasks_created = (await (await db.execute('SELECT COUNT(*) FROM tasks WHERE creator_id = ?', (message.from_user.id,))).fetchone())[0]
        referrals = (await (await db.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (message.from_user.id,))).fetchone())[0]
        total_earned = (await (await db.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'special_task_approved')",
            (message.from_user.id,)
        )).fetchone())[0] or 0
        total_spent = (await (await db.execute(
            "SELECT SUM(ABS(amount)) FROM transactions WHERE user_id = ? AND type IN ('task_create', 'unsubscribe_penalty')",
            (message.from_user.id,)
        )).fetchone())[0] or 0
    premium_badge = " 👑" if (is_premium and premium_expires and datetime.fromisoformat(premium_expires) > datetime.now()) else ""
    prem_info = ""
    if is_premium and premium_expires:
        expires = datetime.fromisoformat(premium_expires)
        if expires > datetime.now():
            prem_info = get_text(lang, 'stats_prem', date=escape_md(expires.strftime('%d.%m.%Y %H:%M')))
    safe_created = escape_md(str(created_at)[:10]) if created_at else "—"
    text = get_text(lang, 'stats_title', badge=premium_badge, balance=balance, completed=tasks_completed,
                    created=tasks_created, refs=referrals, earned=total_earned, spent=total_spent,
                    reg=safe_created, prem=prem_info)
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("top"))
async def cmd_top(message: Message):
    lang = await get_user_lang(message.from_user.id)
    now = datetime.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT u.telegram_id, u.username, SUM(t.amount) as total_earned
            FROM users u JOIN transactions t ON u.telegram_id = t.user_id
            WHERE t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
            AND t.amount > 0 AND t.created_at >= ? AND u.is_banned = 0 AND u.telegram_id != ?
            GROUP BY u.telegram_id ORDER BY total_earned DESC LIMIT 10
        ''', (first_day_this_month.isoformat(), ADMIN_ID))
        top_users = await cursor.fetchall()
        cursor = await db.execute('''
            SELECT SUM(t.amount) FROM transactions t
            WHERE t.user_id = ? AND t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
            AND t.amount > 0 AND t.created_at >= ?
        ''', (message.from_user.id, first_day_this_month.isoformat()))
        user_total = (await cursor.fetchone())[0] or 0
        user_in_top = any(u[0] == message.from_user.id for u in top_users)
        place_num = None
        if not user_in_top and user_total > 0:
            cursor = await db.execute('''
                SELECT COUNT(*) + 1 FROM (
                    SELECT u.telegram_id, SUM(t.amount) as total_earned
                    FROM users u JOIN transactions t ON u.telegram_id = t.user_id
                    WHERE t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
                    AND t.amount > 0 AND t.created_at >= ? AND u.is_banned = 0 AND u.telegram_id != ?
                    GROUP BY u.telegram_id
                ) WHERE total_earned > ?
            ''', (first_day_this_month.isoformat(), ADMIN_ID, user_total))
            place_num = (await cursor.fetchone())[0]
    if not top_users:
        await message.answer(get_text(lang, 'top_empty'))
        return
    text = get_text(lang, 'top_title', month=now.strftime('%B %Y').upper())
    medals = ["🥇", "🥈", "🥉"]
    for i, (telegram_id, username, total_earned) in enumerate(top_users):
        username_display = f"@{escape_md(username)}" if username else "Аноним"
        medal = medals[i] if i < 3 else f"{i+1}."
        if telegram_id == message.from_user.id:
            text += get_text(lang, 'top_line_you', medal=medal, name=username_display, n=total_earned)
        else:
            text += get_text(lang, 'top_line', medal=medal, name=username_display, n=total_earned)
    if not user_in_top and user_total > 0 and place_num:
        text += get_text(lang, 'top_place', p=place_num, n=user_total)
    text += get_text(lang, 'top_prize')
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("test_top"))
async def cmd_test_top(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔️ Только для админа!")
        return
    await message.answer("⏳ Подвожу итоги месяца...")
    await calculate_monthly_top()
    await message.answer("✅ Готово!")


# --- ОБРАБОТЧИКИ CALLBACK ---
@router.callback_query(F.data == "start_menu")
async def cb_start_menu(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_premium FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        is_premium = bool(user[0]) if user else False
    await callback.message.edit_text(get_text(lang, 'main_menu'), reply_markup=get_main_keyboard(is_premium, lang))
    await callback.answer()


@router.callback_query(F.data == "show_lang_menu")
async def cb_show_lang_menu(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'lang_ru'), callback_data="set_lang:ru")],
        [InlineKeyboardButton(text=get_text(lang, 'lang_en'), callback_data="set_lang:en")],
        [InlineKeyboardButton(text=get_text(lang, 'lang_uk'), callback_data="set_lang:uk")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")]
    ])
    await callback.message.edit_text(get_text(lang, 'choose_lang'), reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(callback: CallbackQuery, state: FSMContext):
    new_lang = callback.data.split(":")[1]
    if new_lang not in TRANSLATIONS:
        await callback.answer("⚠️ Неизвестный язык!", show_alert=True)
        return
    await set_user_lang(callback.from_user.id, new_lang)
    lang_names = {'ru': 'Русский', 'en': 'English', 'uk': 'Українська'}
    text = get_text(new_lang, 'lang_changed', lang_name=lang_names[new_lang])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_premium FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        is_premium = bool(user[0]) if user else False
    await callback.message.edit_text(
        f"{text}\n\n{get_text(new_lang, 'main_menu')}",
        reply_markup=get_main_keyboard(is_premium, new_lang),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "show_promo")
async def cb_show_promo(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await callback.message.edit_text(get_text(lang, 'promo_title'))
    await state.set_state(PromoStates.waiting_code)
    await callback.answer()


@router.message(PromoStates.waiting_code)
async def msg_activate_promo(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    promo_code = message.text.strip().upper()
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT id, amount, max_uses, used_count FROM promo_codes WHERE code = ?', (promo_code,))
        promo = await cursor.fetchone()
        if not promo:
            await message.answer(get_text(lang, 'promo_invalid'))
            await state.clear()
            return
        promo_id, amount, max_uses, used_count = promo
        if used_count >= max_uses:
            await message.answer(get_text(lang, 'promo_expired'))
            await state.clear()
            return
        cursor = await db.execute(
            'SELECT id FROM transactions WHERE user_id = ? AND type = ? AND description LIKE ?',
            (message.from_user.id, 'promo_activation', f'%{promo_code}%')
        )
        already_used = await cursor.fetchone()
        if already_used:
            await message.answer(get_text(lang, 'promo_used'))
            await state.clear()
            return
        await db.execute('UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?', (promo_id,))
        await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (amount, message.from_user.id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (message.from_user.id, amount, 'promo_activation', f'Активация промокода {promo_code}')
        )
        await db.commit()
    await state.clear()
    await message.answer(
        get_text(lang, 'promo_success', amount=amount, code=promo_code),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT balance, is_premium, premium_expires_at FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        balance = user[0] if user else 0
        is_premium = bool(user[1]) if user else False
        premium_expires = user[2] if user else None
    premium_badge = " 👑" if is_premium else ""
    premium_info = ""
    if is_premium and premium_expires:
        expires = datetime.fromisoformat(premium_expires)
        premium_info = get_text(lang, 'balance_premium_until', date=escape_md(expires.strftime('%d.%m.%Y %H:%M')))
    stars_price = STARS_PER_1000_TOKENS_PREMIUM if is_premium else STARS_PER_1000_TOKENS
    disc = get_text(lang, 'balance_disc') if is_premium else ""
    text = (
        f"{get_text(lang, 'balance_header', badge=premium_badge, balance=balance)}\n"
        f"{premium_info}\n\n"
        f"{get_text(lang, 'balance_topup_title')}\n"
        f"{get_text(lang, 'balance_stars')}\n"
        f"{get_text(lang, 'balance_stars_rate', rate=stars_price, disc=disc)}\n"
        f"{get_text(lang, 'balance_stars_min', min=MIN_TOKENS_PURCHASE)}\n\n"
        f"{get_text(lang, 'balance_rub')}\n"
        f"{get_text(lang, 'balance_rub_rate', rate=RUB_PER_1000_TOKENS)}\n"
        f"{get_text(lang, 'balance_rub_min', min=MIN_RUB_PURCHASE)}\n\n"
        f"{get_text(lang, 'balance_premium', rub=PREMIUM_PRICE_RUB, stars=PREMIUM_PRICE_STARS)}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_topup_stars'), callback_data="pay_tokens_stars")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_topup_rub'), callback_data="pay_tokens_rub")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_buy_premium', stars=PREMIUM_PRICE_STARS), callback_data="buy_premium")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "pay_tokens_stars")
async def cb_pay_tokens_stars(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_premium, premium_expires_at FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        is_premium = bool(user[0]) if user else False
        premium_expires = user[1] if user else None
    is_premium_active = False
    if is_premium and premium_expires:
        if datetime.fromisoformat(premium_expires) > datetime.now():
            is_premium_active = True
    stars_price = STARS_PER_1000_TOKENS_PREMIUM if is_premium_active else STARS_PER_1000_TOKENS
    disc = get_text(lang, 'balance_disc') if is_premium_active else ""
    text = get_text(lang, 'topup_stars_title', rate=stars_price, disc=disc, min=MIN_TOKENS_PURCHASE,
                    s1=calculate_stars_for_tokens(1000, is_premium_active),
                    s5=calculate_stars_for_tokens(5000, is_premium_active),
                    s10=calculate_stars_for_tokens(10000, is_premium_active))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="balance")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(PayTokensStates.entering_amount)
    await callback.answer()


@router.message(PayTokensStates.entering_amount)
async def msg_pay_tokens_amount(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    try:
        tokens = int(message.text.strip())
    except ValueError:
        await message.answer(get_text(lang, 'num_invalid'))
        return
    if tokens < MIN_TOKENS_PURCHASE:
        await message.answer(get_text(lang, 'balance_stars_min', min=MIN_TOKENS_PURCHASE))
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_premium, premium_expires_at FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        is_premium = bool(user[0]) if user else False
        premium_expires = user[1] if user else None
    is_premium_active = False
    if is_premium and premium_expires:
        if datetime.fromisoformat(premium_expires) > datetime.now():
            is_premium_active = True
    stars_needed = calculate_stars_for_tokens(tokens, is_premium_active)
    rub_equivalent = calculate_rub_for_tokens(tokens)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_pay', stars=stars_needed), callback_data=f"confirm_pay_stars:{tokens}:{stars_needed}")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="balance")]
    ])
    await message.answer(
        get_text(lang, 'pay_confirm', tokens=tokens, stars=stars_needed, rub=rub_equivalent),
        reply_markup=kb, parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data.startswith("confirm_pay_stars:"))
async def cb_confirm_pay_stars(callback: CallbackQuery):
    parts = callback.data.split(":")
    tokens = int(parts[1])
    stars_needed = int(parts[2])
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"⭐️ Пополнение на {tokens} токенов",
        description=f"Пополнение баланса на {tokens} токенов за {stars_needed} Telegram Stars",
        payload=f"tokens_{tokens}_{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{tokens} токенов", amount=stars_needed)]
    )
    await callback.answer()


@router.callback_query(F.data == "pay_tokens_rub")
async def cb_pay_tokens_rub(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    text = get_text(lang, 'topup_rub_title', rate=RUB_PER_1000_TOKENS, min=MIN_RUB_PURCHASE)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_contact_support'), callback_data="support_rub")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="balance")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "support_rub")
async def cb_support_rub(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await callback.message.edit_text(get_text(lang, 'support_rub_text'))
    await state.set_state(SupportStates.waiting_message)
    await callback.answer()


@router.callback_query(F.data == "buy_premium")
async def cb_buy_premium(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_premium, premium_expires_at FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        is_premium = bool(user[0]) if user else False
        premium_expires = user[1] if user else None
    if is_premium and premium_expires and datetime.fromisoformat(premium_expires) > datetime.now():
        expires = datetime.fromisoformat(premium_expires)
        await callback.answer(get_text(lang, 'already_premium', date=expires.strftime('%d.%m.%Y')), show_alert=True)
        return
    text = get_text(lang, 'premium_title', stars=PREMIUM_PRICE_STARS, daily=DAILY_PREMIUM_BONUS,
                    max=PREMIUM_TASKS_PER_DAY, days=PREMIUM_DURATION_DAYS)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_pay_premium', stars=PREMIUM_PRICE_STARS), callback_data="pay_premium_stars")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="balance")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "pay_premium_stars")
async def cb_pay_premium_stars(callback: CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="👑 Премиум-подписка на 30 дней",
        description=f"Премиум-подписка. +{DAILY_PREMIUM_BONUS} токенов каждый день. Срок: {PREMIUM_DURATION_DAYS} дней.",
        payload=f"premium_{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Премиум", amount=PREMIUM_PRICE_STARS)]
    )
    await callback.answer()


@router.message(F.successful_payment)
async def msg_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    user_lang = await get_user_lang(message.from_user.id)
    if payload.startswith("premium_"):
        user_id = int(payload.split("_")[1])
        async with aiosqlite.connect('bot_database.db') as db:
            expires_at = (datetime.now() + timedelta(days=PREMIUM_DURATION_DAYS)).isoformat()
            await db.execute('UPDATE users SET is_premium = 1, premium_expires_at = ? WHERE telegram_id = ?', (expires_at, user_id))
            await db.execute('INSERT INTO premium_purchases (user_id, amount_stars, duration_days) VALUES (?, ?, ?)', (user_id, PREMIUM_PRICE_STARS, PREMIUM_DURATION_DAYS))
            await db.commit()
        expires = datetime.fromisoformat(expires_at)
        await message.answer(
            get_text(user_lang, 'premium_activated', date=escape_md(expires.strftime('%d.%m.%Y %H:%M')), daily=DAILY_PREMIUM_BONUS),
            reply_markup=get_main_keyboard(True, user_lang), parse_mode="Markdown"
        )
    elif payload.startswith("tokens_"):
        parts = payload.split("_")
        tokens = int(parts[1])
        user_id = int(parts[2])
        async with aiosqlite.connect('bot_database.db') as db:
            await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (tokens, user_id))
            await db.execute(
                'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                (user_id, tokens, 'stars_purchase', f'Пополнение через Stars на {tokens} токенов')
            )
            await db.commit()
        await message.answer(
            get_text(user_lang, 'pay_success', n=tokens),
            reply_markup=get_main_keyboard(False, user_lang), parse_mode="Markdown"
        )


# --- МОИ ЗАДАНИЯ (УДАЛЕНИЕ) ---
@router.callback_query(F.data == "my_tasks")
async def cb_my_tasks(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT id, task_type, reward, budget, max_executors, completed_count
            FROM tasks
            WHERE creator_id = ? AND status = 'active'
            ORDER BY id DESC
        ''', (callback.from_user.id,))
        tasks = await cursor.fetchall()
    if not tasks:
        await callback.message.edit_text(get_text(lang, 'no_my_tasks'))
        await callback.answer()
        return
    type_map = {
        "subscribe": get_text(lang, 'type_names_subscribe'),
        "reaction": get_text(lang, 'type_names_reaction'),
        "start_bot": get_text(lang, 'type_names_start_bot'),
        "special": get_text(lang, 'type_names_special'),
    }
    text = get_text(lang, 'my_tasks_title')
    kb_buttons = []
    for task in tasks:
        task_id, task_type, reward, budget, max_exec, completed = task
        refund = budget - (completed * reward)
        type_name = type_map.get(task_type, task_type)
        text += get_text(lang, 'my_task_line', id=task_id, type=type_name, reward=reward, done=completed, max=max_exec, refund=refund)
        text += "\n"
        if refund > 0:
            kb_buttons.append([InlineKeyboardButton(
                text=get_text(lang, 'btn_delete', id=task_id) + f" (+{refund}🪙)",
                callback_data=f"delete_my_task:{task_id}"
            )])
        else:
            kb_buttons.append([InlineKeyboardButton(
                text=f"🔒 #{task_id} (завершено)",
                callback_data="noop"
            )])
    kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("delete_my_task:"))
async def cb_delete_my_task(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'SELECT id, creator_id, budget, reward, completed_count, max_executors FROM tasks WHERE id = ? AND status = ? AND creator_id = ?',
            (task_id, 'active', callback.from_user.id)
        )
        task = await cursor.fetchone()
        if not task:
            await callback.answer(get_text(lang, 'err_no_task'), show_alert=True)
            return
        t_id, creator_id, budget, reward, completed, max_exec = task
        refund = budget - (completed * reward)
        if refund <= 0:
            await callback.answer(get_text(lang, 'task_already_done'), show_alert=True)
            return
        await db.execute("UPDATE tasks SET status = 'deleted' WHERE id = ?", (task_id,))
        await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (refund, creator_id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (creator_id, refund, 'task_delete_refund', f'Возврат токенов при удалении задания #{task_id}')
        )
        await db.commit()
    await callback.message.edit_text(
        get_text(lang, 'task_deleted', id=task_id, refund=refund),
        reply_markup=get_main_keyboard(lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()


# --- СОЗДАНИЕ ЗАДАНИЯ ---
@router.callback_query(F.data == "create_task")
async def cb_create_task(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'SELECT tasks_completed, balance, is_premium, premium_expires_at FROM users WHERE telegram_id = ?',
            (callback.from_user.id,)
        )
        user = await cursor.fetchone()
        tasks_completed, balance, is_premium, premium_expires = user
    is_premium_active = False
    if is_premium and premium_expires:
        if datetime.fromisoformat(premium_expires) > datetime.now():
            is_premium_active = True
    can_create, limit = await check_daily_task_limit(callback.from_user.id)
    if not can_create:
        await callback.answer(get_text(lang, 'err_limit', n=limit), show_alert=True)
        return
    if not is_premium_active and tasks_completed < 3:
        await callback.answer(get_text(lang, 'err_need_3', n=tasks_completed), show_alert=True)
        return
    if balance < 100:
        await callback.answer(get_text(lang, 'err_no_tokens'), show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'type_subscribe'), callback_data="task_type:subscribe")],
        [InlineKeyboardButton(text=get_text(lang, 'type_reaction'), callback_data="task_type:reaction")],
        [InlineKeyboardButton(text=get_text(lang, 'type_start_bot'), callback_data="task_type:start_bot")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task")]
    ])
    await callback.message.edit_text(get_text(lang, 'create_title'), reply_markup=kb)
    await state.set_state(CreateTaskStates.choosing_type)
    await callback.answer()


@router.callback_query(F.data.startswith("task_type:"), CreateTaskStates.choosing_type)
async def cb_task_type(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    task_type = callback.data.split(":")[1]
    await state.update_data(task_type=task_type)
    type_map = {
        "subscribe": get_text(lang, 'type_subscribe'),
        "reaction": get_text(lang, 'type_reaction'),
        "start_bot": get_text(lang, 'type_start_bot'),
    }
    warning = ""
    if task_type == 'subscribe':
        warning = "\n\n" + get_text(lang, 'subscribe_warning')
    await callback.message.edit_text(
        get_text(lang, 'link_prompt', type=type_map[task_type]) + warning,
        parse_mode="Markdown"
    )
    await state.set_state(CreateTaskStates.entering_link)
    await callback.answer()


@router.message(CreateTaskStates.entering_link)
async def msg_enter_link(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    link = message.text.strip()
    if link.startswith('@'):
        link = f"https://t.me/{link[1:]}"
    elif not link.startswith(('https://t.me/', 'http://t.me/')):
        if all(c.isalnum() or c == '_' for c in link):
            link = f"https://t.me/{link}"
        else:
            await message.answer(get_text(lang, 'link_invalid'))
            return
    await state.update_data(link=link)
    await message.answer(get_text(lang, 'link_accepted'))
    await state.set_state(CreateTaskStates.entering_reward)


@router.message(CreateTaskStates.entering_reward)
async def msg_enter_reward(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    try:
        reward = int(message.text.strip())
    except ValueError:
        await message.answer(get_text(lang, 'num_invalid'))
        return
    if reward < 100:
        await message.answer(get_text(lang, 'reward_min'))
        return
    await state.update_data(reward=reward)
    await message.answer(get_text(lang, 'reward_set', reward=reward))
    await state.set_state(CreateTaskStates.entering_budget)


@router.message(CreateTaskStates.entering_budget)
async def msg_enter_budget(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    try:
        budget = int(message.text.strip())
    except ValueError:
        await message.answer(get_text(lang, 'budget_invalid'))
        return
    data = await state.get_data()
    reward = data['reward']
    if budget < reward:
        await message.answer(get_text(lang, 'budget_low', reward=reward))
        return
    
    # Получаем баланс с проверкой на существование пользователя
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT balance FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        
        if not user:
            await message.answer(get_text(lang, 'err_no_reg'))
            await state.clear()
            return
        
        balance = user[0]
    
    if balance < budget:
        await message.answer(get_text(lang, 'budget_insufficient', balance=balance, budget=budget))
        return
    
    max_executors = budget // reward
    remainder = budget - (max_executors * reward)
    await state.update_data(budget=budget, max_executors=max_executors, remainder=remainder)
    type_map = {
        "subscribe": get_text(lang, 'type_subscribe'),
        "reaction": get_text(lang, 'type_reaction'),
        "start_bot": get_text(lang, 'type_start_bot'),
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_confirm'), callback_data="confirm_task")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task")]
    ])
    await message.answer(
        get_text(lang, 'task_summary', type=type_map[data['task_type']], link=data['link'],
                 reward=reward, budget=budget, max=max_executors, rem=remainder),
        reply_markup=kb
    )
    await state.set_state(CreateTaskStates.confirming)


@router.callback_query(F.data == "confirm_task", CreateTaskStates.confirming)
async def cb_confirm_task(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    data = await state.get_data()
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('''
            INSERT INTO tasks (creator_id, task_type, link, reward, budget, max_executors, completed_count, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'active')
        ''', (callback.from_user.id, data['task_type'], data['link'], data['reward'], data['budget'], data['max_executors']))
        await db.execute('UPDATE users SET balance = balance - ? WHERE telegram_id = ?', (data['budget'], callback.from_user.id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (callback.from_user.id, -data['budget'], 'task_create', f"Создание задания #{data['task_type']}")
        )
        await db.commit()
    await increment_daily_task_count(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(get_text(lang, 'task_created'))
    await callback.answer()


@router.callback_query(F.data == "cancel_task")
async def cb_cancel_task(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(get_text(lang, 'task_cancelled'))
    await callback.answer()


@router.callback_query(F.data == "view_tasks")
async def cb_view_tasks(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT t.id, t.task_type, t.link, t.reward, t.max_executors, t.completed_count, u.is_premium
            FROM tasks t LEFT JOIN users u ON t.creator_id = u.telegram_id
            WHERE t.status = 'active'
              AND t.completed_count < t.max_executors
              AND t.creator_id != ?
              AND NOT EXISTS (
                  SELECT 1 FROM task_executions te
                  WHERE te.task_id = t.id AND te.executor_id = ?
              )
            ORDER BY u.is_premium DESC, t.created_at DESC LIMIT 20
        ''', (callback.from_user.id, callback.from_user.id))
        tasks = await cursor.fetchall()
    if not tasks:
        await callback.message.edit_text(get_text(lang, 'no_tasks'))
        await callback.answer()
        return
    type_map = {
        "subscribe": get_text(lang, 'type_names_subscribe'),
        "reaction": get_text(lang, 'type_names_reaction'),
        "start_bot": get_text(lang, 'type_names_start_bot'),
        "special": get_text(lang, 'type_names_special'),
    }
    text = get_text(lang, 'tasks_title')
    kb_buttons = []
    for task in tasks:
        task_id, task_type, link, reward, max_exec, completed, is_premium = task
        remaining = max_exec - completed
        mark = "👑 " if is_premium else ""
        text += get_text(lang, 'tasks_line', mark=mark, id=task_id, type=type_map.get(task_type, task_type), reward=reward, left=remaining)
        kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_complete', id=task_id), callback_data=f"do_task:{task_id}")])
        kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_report', id=task_id), callback_data=f"report_task:{task_id}")])
    kb_buttons.append([InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("do_task:"))
async def cb_do_task(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_banned FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        if user and user[0] == 1:
            await callback.answer(get_text(lang, 'err_banned'), show_alert=True)
            return
        cursor = await db.execute(
            'SELECT id, creator_id, task_type, link, reward, max_executors, completed_count, status, description FROM tasks WHERE id = ?',
            (task_id,)
        )
        task = await cursor.fetchone()
        if not task:
            await callback.answer(get_text(lang, 'err_no_task'), show_alert=True)
            return
        task_id, creator_id, task_type, link, reward, max_exec, completed, status, description = task
        if status != 'active' or completed >= max_exec:
            await callback.answer(get_text(lang, 'err_done'), show_alert=True)
            return
        if creator_id == callback.from_user.id:
            await callback.answer(get_text(lang, 'err_own'), show_alert=True)
            return
        cursor = await db.execute('SELECT id FROM task_executions WHERE task_id = ? AND executor_id = ?', (task_id, callback.from_user.id))
        existing = await cursor.fetchone()
        if existing:
            await callback.answer(get_text(lang, 'err_repeat'), show_alert=True)
            return
    await state.update_data(
        task_id=task_id, creator_id=creator_id, task_type=task_type, link=link, reward=reward,
        task_message_id=callback.message.message_id
    )
    type_map = {
        "subscribe": get_text(lang, 'type_subscribe'),
        "reaction": get_text(lang, 'type_reaction'),
        "start_bot": get_text(lang, 'type_start_bot'),
        "special": get_text(lang, 'type_special'),
    }
    if task_type == 'special':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'btn_send_report'), callback_data=f"send_report:{task_id}")],
            [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task_execution")]
        ])
        text = get_text(lang, 'do_task_special', id=task_id, type=type_map[task_type], reward=reward, desc=description or "—")
    elif task_type == 'subscribe':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Подписаться на канал", url=link)],
            [InlineKeyboardButton(text=get_text(lang, 'btn_check'), callback_data=f"check_task:{task_id}")],
            [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task_execution")]
        ])
        text = (
            get_text(lang, 'do_task_title', id=task_id, type=type_map[task_type], reward=reward, penalty=UNSUBSCRIBE_PENALTY)
            + "\n\n" + get_text(lang, 'subscribe_warning')
        )
    elif task_type == 'start_bot':
        bot_username = extract_bot_username(link)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'btn_go_task'), url=link)],
            [InlineKeyboardButton(text=get_text(lang, 'btn_check'), callback_data=f"confirm_start_bot:{task_id}")],
            [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task_execution")]
        ])
        text = get_text(lang, 'do_task_start_bot', id=task_id, type=type_map[task_type], reward=reward, bot_username=bot_username)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'btn_go_task'), url=link)],
            [InlineKeyboardButton(text=get_text(lang, 'btn_check'), callback_data=f"check_task:{task_id}")],
            [InlineKeyboardButton(text=get_text(lang, 'btn_cancel'), callback_data="cancel_task_execution")]
        ])
        text = get_text(lang, 'do_task_title', id=task_id, type=type_map[task_type], reward=reward, penalty=UNSUBSCRIBE_PENALTY)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# --- ПРОВЕРКА ЗАПУСКА БОТА ЧЕРЕЗ ПЕРЕСЫЛКУ ---
@router.callback_query(F.data.startswith("confirm_start_bot:"))
async def cb_confirm_start_bot(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT id FROM task_executions WHERE task_id = ? AND executor_id = ?', (task_id, callback.from_user.id))
        existing = await cursor.fetchone()
        if existing:
            await callback.answer(get_text(lang, 'err_repeat'), show_alert=True)
            return
    data = await state.get_data()
    if data.get('task_id') != task_id:
        await callback.answer(get_text(lang, 'err_expired'), show_alert=True)
        return
    link = data['link']
    bot_username = extract_bot_username(link)
    await state.update_data(
        expected_bot_username=bot_username,
        task_message_id=callback.message.message_id
    )
    # Отправляем НОВОЕ сообщение с просьбой переслать
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text(lang, 'forward_request', bot_username=bot_username),
        parse_mode="Markdown"
    )
    await state.set_state(ConfirmBotStates.waiting_forward)
    await callback.answer()


@router.message(ConfirmBotStates.waiting_forward)
async def msg_confirm_start_bot(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    data = await state.get_data()
    expected_username = data.get('expected_bot_username', '').lower()
    task_id = data.get('task_id')
    reward = data.get('reward')
    task_message_id = data.get('task_message_id')

    if not message.forward_origin:
        await message.answer(
            get_text(lang, 'forward_not_forwarded', bot_username=expected_username),
            parse_mode="Markdown"
        )
        return

    sender_username = None
    if hasattr(message.forward_origin, 'sender_chat') and message.forward_origin.sender_chat:
        sender_username = (message.forward_origin.sender_chat.username or "").lower()
    elif hasattr(message.forward_origin, 'sender_user') and message.forward_origin.sender_user:
        sender_username = (message.forward_origin.sender_user.username or "").lower()

    if not sender_username:
        await message.answer(
            get_text(lang, 'forward_unknown_source', bot_username=expected_username),
            parse_mode="Markdown"
        )
        return

    if sender_username != expected_username:
        await message.answer(
            get_text(lang, 'forward_wrong_bot', expected=expected_username),
            parse_mode="Markdown"
        )
        return

    await state.clear()

    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute(
            'UPDATE users SET balance = balance + ?, tasks_completed = tasks_completed + 1 WHERE telegram_id = ?',
            (reward, message.from_user.id)
        )
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (message.from_user.id, reward, 'task_complete', f'Выполнение задания #{task_id} (запуск бота @{expected_username})')
        )
        await db.execute(
            'INSERT INTO task_executions (task_id, executor_id, completed_at) VALUES (?, ?, ?)',
            (task_id, message.from_user.id, asyncio.get_event_loop().time())
        )
        await db.execute('UPDATE tasks SET completed_count = completed_count + 1 WHERE id = ?', (task_id,))
        cursor = await db.execute('SELECT completed_count, max_executors, budget, reward, creator_id FROM tasks WHERE id = ?', (task_id,))
        task_info = await cursor.fetchone()
        if task_info:
            completed_count, max_executors, budget, task_reward, creator_id = task_info
            if completed_count >= max_executors:
                remainder = budget - (max_executors * task_reward)
                if remainder > 0:
                    await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (remainder, creator_id))
                await db.execute('UPDATE tasks SET status = ? WHERE id = ?', ('completed', task_id))
                try:
                    await bot.send_message(creator_id, f"✅ Твоё задание #{task_id} полностью выполнено!\nВернулось: {remainder} токенов")
                except:
                    pass
        await db.commit()

    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT referrer_id FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        referrer_id = user[0] if user else None
        if referrer_id:
            referral_bonus = int(reward * 0.1)
            if referral_bonus > 0:
                await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (referral_bonus, referrer_id))
                await db.execute(
                    'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                    (referrer_id, referral_bonus, 'referral_bonus', f'10% от задания #{task_id} реферала')
                )
                await db.commit()

    # Редактируем исходное сообщение задания (убираем кнопки)
    if task_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=task_message_id,
                text=f"✅ Задание #{task_id} выполнено!\n\nТебе начислено: {reward} токенов",
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Failed to edit task message: {e}")

    await message.answer(
        get_text(lang, 'forward_success', n=reward),
        reply_markup=get_main_keyboard(lang=lang)
    )


@router.callback_query(F.data.startswith("send_report:"))
async def cb_send_report(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    if data.get('task_id') != task_id:
        await callback.answer(get_text(lang, 'err_expired'), show_alert=True)
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT id, status FROM special_submissions WHERE task_id = ? AND user_id = ?', (task_id, callback.from_user.id))
        existing = await cursor.fetchone()
        if existing:
            sub_id, sub_status = existing
            if sub_status == 'pending':
                await callback.answer(get_text(lang, 'report_wait'), show_alert=True)
                return
            elif sub_status in ['approved', 'rejected']:
                await callback.answer(get_text(lang, 'report_already'), show_alert=True)
                return
    await callback.message.edit_text(get_text(lang, 'send_screenshot'))
    await state.set_state(ReportStates.waiting_screenshot)
    await callback.answer()


@router.message(ReportStates.waiting_screenshot, F.photo | F.document)
async def msg_report_screenshot(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    data = await state.get_data()
    task_id = data.get('task_id')
    reward = data.get('reward')
    if not task_id:
        await message.answer(get_text(lang, 'err_expired'))
        await state.clear()
        return
    if message.photo:
        screenshot_file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        screenshot_file_id = message.document.file_id
    else:
        await message.answer(get_text(lang, 'send_screenshot'))
        return
    caption = message.caption or ""
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'INSERT INTO special_submissions (task_id, user_id, screenshot_file_id, caption, status) VALUES (?, ?, ?, ?, ?)',
            (task_id, message.from_user.id, screenshot_file_id, caption, 'pending')
        )
        submission_id = cursor.lastrowid
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Одобрить и начислить {reward} токенов", callback_data=f"approve_report:{submission_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_report:{submission_id}")]
    ])
    await bot.send_photo(
        ADMIN_ID,
        photo=screenshot_file_id,
        caption=(
            f"⭐️ *Новый отчёт по особому заданию!*\n\n"
            f"ID отчёта: {submission_id}\n"
            f"Задание: #{task_id}\n"
            f"Пользователь: @{escape_md(message.from_user.username or '')} (ID: {message.from_user.id})\n"
            f"Награда: {reward} токенов\n"
            f"Подпись: {escape_md(caption) if caption else '—'}\n\n"
            f"Нажми кнопку для одобрения или отклонения:"
        ),
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.clear()
    await message.answer(get_text(lang, 'report_sent'))


@router.callback_query(F.data.startswith("approve_report:"))
async def cb_approve_report(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    submission_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT task_id, user_id, status FROM special_submissions WHERE id = ?', (submission_id,))
        submission = await cursor.fetchone()
        if not submission:
            await callback.answer("❌ Отчёт не найден!", show_alert=True)
            return
        task_id, user_id, status = submission
        if status != 'pending':
            await callback.answer(f"⚠️ Отчёт уже {status}!", show_alert=True)
            return
        cursor = await db.execute('SELECT reward FROM tasks WHERE id = ?', (task_id,))
        task = await cursor.fetchone()
        reward = task[0] if task else 0
        await db.execute('UPDATE special_submissions SET status = ? WHERE id = ?', ('approved', submission_id))
        await db.execute('UPDATE users SET balance = balance + ?, tasks_completed = tasks_completed + 1 WHERE telegram_id = ?', (reward, user_id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (user_id, reward, 'special_task_approved', f'Одобрен отчёт по особому заданию #{task_id}')
        )
        await db.execute('UPDATE tasks SET completed_count = completed_count + 1 WHERE id = ?', (task_id,))
        cursor = await db.execute('SELECT completed_count, max_executors, budget, reward, creator_id FROM tasks WHERE id = ?', (task_id,))
        task_info = await cursor.fetchone()
        completed_count = max_executors = budget = task_reward = creator_id = 0
        if task_info:
            completed_count, max_executors, budget, task_reward, creator_id = task_info
            if completed_count >= max_executors:
                remainder = budget - (max_executors * task_reward)
                if remainder > 0:
                    await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (remainder, creator_id))
                await db.execute('UPDATE tasks SET status = ? WHERE id = ?', ('completed', task_id))
                try:
                    await bot.send_message(creator_id, f"✅ Твоё особое задание #{task_id} полностью выполнено!\nВернулось: {remainder} токенов")
                except:
                    pass
        await db.commit()
    user_lang = await get_user_lang(user_id)
    try:
        await bot.send_message(user_id, get_text(user_lang, 'report_approved', amount=reward), parse_mode="Markdown")
    except:
        pass
    await callback.message.edit_text(
        f"✅ Отчёт #{submission_id} одобрен!\n\n"
        f"Пользователю ID {user_id} начислено {reward} токенов.\n"
        f"Задание #{task_id}: выполнено {completed_count}/{max_executors}"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reject_report:"))
async def cb_reject_report(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    submission_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT task_id, user_id, status FROM special_submissions WHERE id = ?', (submission_id,))
        submission = await cursor.fetchone()
        if not submission:
            await callback.answer("❌ Отчёт не найден!", show_alert=True)
            return
        task_id, user_id, status = submission
        if status != 'pending':
            await callback.answer(f"⚠️ Отчёт уже {status}!", show_alert=True)
            return
        await db.execute('UPDATE special_submissions SET status = ? WHERE id = ?', ('rejected', submission_id))
        await db.commit()
    user_lang = await get_user_lang(user_id)
    try:
        await bot.send_message(user_id, get_text(user_lang, 'report_rejected'), parse_mode="Markdown")
    except:
        pass
    await callback.message.edit_text(
        f"❌ Отчёт #{submission_id} отклонён.\n\n"
        f"Пользователь ID {user_id} уведомлён."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_task:"))
async def cb_check_task(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT id FROM task_executions WHERE task_id = ? AND executor_id = ?', (task_id, callback.from_user.id))
        existing = await cursor.fetchone()
        if existing:
            await callback.answer(get_text(lang, 'err_repeat'), show_alert=True)
            return
    data = await state.get_data()
    if data.get('task_id') != task_id:
        await callback.answer(get_text(lang, 'err_expired'), show_alert=True)
        return
    task_type = data['task_type']
    link = data['link']
    reward = data['reward']
    if task_type == 'subscribe':
        try:
            channel_username = link.replace("https://t.me/", "").replace("http://t.me/", "").strip()
            if '/' in channel_username:
                channel_username = channel_username.split('/')[0]
            if not channel_username.startswith('@'):
                channel_username = f"@{channel_username}"
            if channel_username.startswith('@+'):
                await callback.answer(get_text(lang, 'err_invalid_link'), show_alert=True)
                return
            chat = await bot.get_chat(channel_username)
            chat_id = chat.id
            member = await bot.get_chat_member(chat_id, callback.from_user.id)
            if member.status not in ['member', 'administrator', 'creator']:
                await callback.answer(get_text(lang, 'err_not_subscribed'), show_alert=True)
                return
        except Exception as e:
            error_msg = str(e)
            if "member list is inaccessible" in error_msg:
                await callback.answer(get_text(lang, 'err_member_inaccessible'), show_alert=True)
            elif "chat not found" in error_msg:
                await callback.answer(get_text(lang, 'err_chat_not_found', name=channel_username), show_alert=True)
            else:
                await callback.answer(get_text(lang, 'err_check', err=error_msg[:150]), show_alert=True)
            return
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('UPDATE users SET balance = balance + ?, tasks_completed = tasks_completed + 1 WHERE telegram_id = ?', (reward, callback.from_user.id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (callback.from_user.id, reward, 'task_complete', f'Выполнение задания #{task_id}')
        )
        await db.execute(
            'INSERT INTO task_executions (task_id, executor_id, completed_at) VALUES (?, ?, ?)',
            (task_id, callback.from_user.id, asyncio.get_event_loop().time())
        )
        await db.execute('UPDATE tasks SET completed_count = completed_count + 1 WHERE id = ?', (task_id,))
        cursor = await db.execute('SELECT completed_count, max_executors, budget, reward, creator_id FROM tasks WHERE id = ?', (task_id,))
        task_info = await cursor.fetchone()
        completed_count, max_executors, budget, task_reward, creator_id = task_info
        if completed_count >= max_executors:
            remainder = budget - (max_executors * task_reward)
            if remainder > 0:
                await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (remainder, creator_id))
                await db.execute(
                    'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                    (creator_id, remainder, 'task_remainder', f'Возврат остатка по заданию #{task_id}')
                )
            await db.execute('UPDATE tasks SET status = ? WHERE id = ?', ('completed', task_id))
            try:
                await bot.send_message(creator_id, f"✅ Твоё задание #{task_id} полностью выполнено!\nВернулось: {remainder} токенов")
            except:
                pass
        await db.commit()
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT referrer_id FROM users WHERE telegram_id = ?', (callback.from_user.id,))
        user = await cursor.fetchone()
        referrer_id = user[0] if user else None
        if referrer_id:
            referral_bonus = int(reward * 0.1)
            if referral_bonus > 0:
                await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (referral_bonus, referrer_id))
                await db.execute(
                    'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                    (referrer_id, referral_bonus, 'referral_bonus', f'10% от задания #{task_id} реферала')
                )
                await db.commit()
    await state.clear()
    await callback.message.edit_text(get_text(lang, 'task_done', n=reward))
    await callback.answer()


@router.callback_query(F.data == "cancel_task_execution")
async def cb_cancel_task_execution(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(get_text(lang, 'cancel_exec'))
    await callback.answer()


@router.callback_query(F.data.startswith("report_task:"))
async def cb_report_task(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT id FROM task_reports WHERE task_id = ? AND reporter_id = ?', (task_id, callback.from_user.id))
        existing = await cursor.fetchone()
        if existing:
            await callback.answer(get_text(lang, 'report_dup'), show_alert=True)
            return
        cursor = await db.execute('SELECT creator_id, link FROM tasks WHERE id = ?', (task_id,))
        task = await cursor.fetchone()
        if not task:
            await callback.answer(get_text(lang, 'err_no_task'), show_alert=True)
            return
        creator_id, link = task
        if creator_id == callback.from_user.id:
            await callback.answer(get_text(lang, 'report_self'), show_alert=True)
            return
        await db.execute('INSERT INTO task_reports (task_id, reporter_id, reason) VALUES (?, ?, ?)', (task_id, callback.from_user.id, 'Не указана'))
        cursor = await db.execute('SELECT COUNT(*) FROM task_reports WHERE task_id = ?', (task_id,))
        report_count = (await cursor.fetchone())[0]
        await db.commit()
    if report_count >= 3:
        async with aiosqlite.connect('bot_database.db') as db:
            await db.execute("UPDATE tasks SET status = 'reported' WHERE id = ?", (task_id,))
            await db.commit()
        await bot.send_message(
            ADMIN_ID,
            f"🚨 *Задание #{task_id} скрыто по жалобам!*\n\nКоличество жалоб: {report_count}\nСсылка: {link}\nСоздатель: ID {creator_id}",
            parse_mode="Markdown"
        )
        await callback.answer(get_text(lang, 'report_hidden', n=report_count), show_alert=True)
    else:
        await callback.answer(get_text(lang, 'report_ok', n=report_count), show_alert=True)


@router.callback_query(F.data == "referrals")
async def cb_referrals(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (callback.from_user.id,))
        ref_count = (await cursor.fetchone())[0]
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref={callback.from_user.id}"
    safe_link = escape_md(referral_link)
    text = get_text(lang, 'ref_title', n=ref_count, link=safe_link)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'btn_copy_link'), url=referral_link)],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await callback.message.edit_text(get_text(lang, 'support_title'))
    await state.set_state(SupportStates.waiting_message)
    await callback.answer()


@router.message(SupportStates.waiting_message)
async def msg_support(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT is_premium, premium_expires_at FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        is_premium = False
        if user and user[0] and user[1] and datetime.fromisoformat(user[1]) > datetime.now():
            is_premium = True
    priority_mark = "🔴 [ПРИОРИТЕТ] " if is_premium else ""
    await bot.send_message(
        ADMIN_ID,
        f"{priority_mark}🛎 Сообщение от @{escape_md(message.from_user.username or '')} (ID: {message.from_user.id}):\n\n{message.text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_to:{message.from_user.id}")]
        ])
    )
    await state.clear()
    await message.answer(get_text(lang, 'support_sent'))


@router.callback_query(F.data.startswith("reply_to:"))
async def cb_reply_to_user(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(reply_to_user_id=user_id)
    await callback.message.edit_text(
        f"💬 *Ответ пользователю ID {user_id}*\n\nОтправь сообщение, которое нужно переслать:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.replying_to_user)
    await callback.answer()


@router.message(AdminStates.replying_to_user)
async def msg_admin_reply(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    target_user_id = data.get('reply_to_user_id')
    if not target_user_id:
        await message.answer("⚠️ Ошибка: не указан пользователь.")
        await state.clear()
        return
    try:
        await message.copy_to(target_user_id)
        await message.answer(f"✅ Сообщение отправлено пользователю ID {target_user_id}!")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {str(e)}")
    await state.clear()


@router.callback_query(F.data == "show_top")
async def cb_show_top(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    now = datetime.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''
            SELECT u.telegram_id, u.username, SUM(t.amount) as total_earned
            FROM users u JOIN transactions t ON u.telegram_id = t.user_id
            WHERE t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
            AND t.amount > 0 AND t.created_at >= ? AND u.is_banned = 0 AND u.telegram_id != ?
            GROUP BY u.telegram_id ORDER BY total_earned DESC LIMIT 10
        ''', (first_day_this_month.isoformat(), ADMIN_ID))
        top_users = await cursor.fetchall()
        cursor = await db.execute('''
            SELECT SUM(t.amount) FROM transactions t
            WHERE t.user_id = ? AND t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
            AND t.amount > 0 AND t.created_at >= ?
        ''', (callback.from_user.id, first_day_this_month.isoformat()))
        user_total = (await cursor.fetchone())[0] or 0
        user_in_top = any(u[0] == callback.from_user.id for u in top_users)
        place_num = None
        if not user_in_top and user_total > 0:
            cursor = await db.execute('''
                SELECT COUNT(*) + 1 FROM (
                    SELECT u.telegram_id, SUM(t.amount) as total_earned
                    FROM users u JOIN transactions t ON u.telegram_id = t.user_id
                    WHERE t.type IN ('task_complete', 'bonus', 'referral_bonus', 'premium_daily', 'admin_add', 'special_task_approved')
                    AND t.amount > 0 AND t.created_at >= ? AND u.is_banned = 0 AND u.telegram_id != ?
                    GROUP BY u.telegram_id
                ) WHERE total_earned > ?
            ''', (first_day_this_month.isoformat(), ADMIN_ID, user_total))
            place_num = (await cursor.fetchone())[0]
    if not top_users:
        await callback.message.edit_text(get_text(lang, 'top_empty'))
        await callback.answer()
        return
    text = get_text(lang, 'top_title', month=now.strftime('%B %Y').upper())
    medals = ["🥇", "🥈", "🥉"]
    for i, (telegram_id, username, total_earned) in enumerate(top_users):
        username_display = f"@{escape_md(username)}" if username else "Аноним"
        medal = medals[i] if i < 3 else f"{i+1}."
        if telegram_id == callback.from_user.id:
            text += get_text(lang, 'top_line_you', medal=medal, name=username_display, n=total_earned)
        else:
            text += get_text(lang, 'top_line', medal=medal, name=username_display, n=total_earned)
    if not user_in_top and user_total > 0 and place_num:
        text += get_text(lang, 'top_place', p=place_num, n=user_total)
    text += get_text(lang, 'top_prize')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'refresh'), callback_data="show_top")],
        [InlineKeyboardButton(text=get_text(lang, 'btn_back'), callback_data="start_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# --- АДМИН-ПАНЕЛЬ ---
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔️ У тебя нет доступа к админ-панели!")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="💬 Написать пользователю", callback_data="admin_write_to_user")],
        [InlineKeyboardButton(text="➕ Создать задание", callback_data="admin_create_task")],
        [InlineKeyboardButton(text="⭐️ Особое задание", callback_data="admin_create_special")],
        [InlineKeyboardButton(text="🗑 Удалить задание", callback_data="admin_delete_task")],
        [InlineKeyboardButton(text="🗑 Удалить все задания", callback_data="admin_delete_all_tasks")],
        [InlineKeyboardButton(text="👑 Выдать премиум", callback_data="admin_add_premium")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_ban")],
        [InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_unban")],
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="❌ Удалить промокод", callback_data="admin_delete_promo")],
        [InlineKeyboardButton(text="💰 Начислить токены", callback_data="admin_add_tokens")],
    ])
    await message.answer("🛠 *Админ-панель:*\n\nВыбери действие:", reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    async with aiosqlite.connect('bot_database.db') as db:
        total_users = (await (await db.execute('SELECT COUNT(*) FROM users')).fetchone())[0]
        active_tasks = (await (await db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'active'")).fetchone())[0]
        completed_tasks = (await (await db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")).fetchone())[0]
        total_turnover = (await (await db.execute("SELECT SUM(ABS(amount)) FROM transactions")).fetchone())[0] or 0
        banned_users = (await (await db.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')).fetchone())[0]
        premium_users = (await (await db.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1')).fetchone())[0]
    text = (
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"👑 Премиум-пользователей: {premium_users}\n"
        f"🚫 Заблокировано: {banned_users}\n"
        f"📋 Активных заданий: {active_tasks}\n"
        f"✅ Завершенных заданий: {completed_tasks}\n"
        f"💰 Общий оборот токенов: {total_turnover}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="💬 Написать пользователю", callback_data="admin_write_to_user")],
        [InlineKeyboardButton(text="➕ Создать задание", callback_data="admin_create_task")],
        [InlineKeyboardButton(text="⭐️ Особое задание", callback_data="admin_create_special")],
        [InlineKeyboardButton(text="🗑 Удалить задание", callback_data="admin_delete_task")],
        [InlineKeyboardButton(text="🗑 Удалить все задания", callback_data="admin_delete_all_tasks")],
        [InlineKeyboardButton(text="👑 Выдать премиум", callback_data="admin_add_premium")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_ban")],
        [InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_unban")],
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="❌ Удалить промокод", callback_data="admin_delete_promo")],
        [InlineKeyboardButton(text="💰 Начислить токены", callback_data="admin_add_tokens")],
    ])
    await callback.message.edit_text("🛠 Админ-панель:\n\nВыбери действие:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin_mailing")
async def cb_admin_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("📢 *Рассылка*\n\nОтправь сообщение для рассылки (текст, фото или стикер):", parse_mode="Markdown")
    await state.set_state(AdminStates.mailing_message)
    await callback.answer()


@router.message(AdminStates.mailing_message)
async def msg_admin_mailing(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if message.photo:
        photo_file_id = message.photo[-1].file_id
        caption = message.caption or ""
        await state.update_data(mailing_photo=photo_file_id, mailing_caption=caption, has_photo=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="confirm_mailing")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_mailing")]
        ])
        await message.answer_photo(photo=photo_file_id, caption=f"📢 *Превью:*\n\n{caption}", reply_markup=kb, parse_mode="Markdown")
    elif message.sticker:
        sticker_file_id = message.sticker.file_id
        await state.update_data(mailing_sticker=sticker_file_id, has_sticker=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="confirm_mailing")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_mailing")]
        ])
        await message.answer_sticker(sticker=sticker_file_id, reply_markup=kb)
        await message.answer("📢 *Превью выше.* Нажми кнопку для отправки:", parse_mode="Markdown")
    elif message.text:
        await state.update_data(mailing_text=message.text, has_photo=False, has_sticker=False)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="confirm_mailing")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_mailing")]
        ])
        await message.answer(f"📢 *Превью:*\n\n{message.text}", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("⚠️ Отправь текст, фото или стикер!")


@router.callback_query(F.data == "confirm_mailing")
async def cb_confirm_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    data = await state.get_data()
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT telegram_id FROM users WHERE is_banned = 0')
        users = await cursor.fetchall()
    success_count = 0
    fail_count = 0
    total = len(users)
    progress_msg = await callback.message.answer(f"📢 Рассылка... 0/{total}")
    for i, user in enumerate(users):
        user_id = user[0]
        try:
            if data.get('has_photo'):
                await bot.send_photo(user_id, photo=data['mailing_photo'], caption=data.get('mailing_caption', ''))
            elif data.get('has_sticker'):
                await bot.send_sticker(user_id, sticker=data['mailing_sticker'])
            else:
                await bot.send_message(user_id, data.get('mailing_text', ''))
            success_count += 1
            if (i + 1) % 10 == 0:
                try:
                    await progress_msg.edit_text(f"📢 Рассылка... {success_count}/{total}")
                except:
                    pass
            await asyncio.sleep(0.05)
        except:
            fail_count += 1
    await state.clear()
    try:
        await progress_msg.edit_text(f"✅ Рассылка завершена!\n\n👥 Всего: {total}\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")
    except:
        await callback.message.answer(f"✅ Рассылка завершена!\n\n👥 Всего: {total}\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")
    await callback.answer()


@router.callback_query(F.data == "cancel_mailing")
async def cb_cancel_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена.")
    await callback.answer()


@router.callback_query(F.data == "admin_write_to_user")
async def cb_admin_write_to_user(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("💬 *Написать пользователю*\n\nВведи ID или username:", parse_mode="Markdown")
    await state.set_state(AdminStates.write_to_user_search)
    await callback.answer()


@router.message(AdminStates.write_to_user_search)
async def msg_admin_write_to_user_search(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    search_value = message.text.strip().lstrip('@')
    async with aiosqlite.connect('bot_database.db') as db:
        if search_value.isdigit():
            cursor = await db.execute('SELECT telegram_id, username FROM users WHERE telegram_id = ?', (int(search_value),))
        else:
            cursor = await db.execute('SELECT telegram_id, username FROM users WHERE username = ?', (search_value,))
        user = await cursor.fetchone()
        if not user:
            await message.answer("❌ Пользователь не найден!")
            await state.clear()
            return
        user_id, username = user
        username_display = f"@{username}" if username else f"ID {user_id}"
    await state.update_data(write_to_user_id=user_id, write_to_username=username_display)
    await message.answer(f"✅ Найден: {username_display} (ID: {user_id})\n\nОтправь сообщение:")
    await state.set_state(AdminStates.write_to_user_message)


@router.message(AdminStates.write_to_user_message)
async def msg_admin_write_to_user_message(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    target_user_id = data.get('write_to_user_id')
    target_username = data.get('write_to_username', 'неизвестно')
    if not target_user_id:
        await message.answer("⚠️ Ошибка.")
        await state.clear()
        return
    try:
        await message.copy_to(target_user_id)
        await message.answer(f"✅ Сообщение отправлено {target_username}!")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {str(e)}")
    await state.clear()


@router.callback_query(F.data == "admin_create_task")
async def cb_admin_create_task(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписка на канал", callback_data="admin_task_type:subscribe")],
        [InlineKeyboardButton(text="👍 Реакция на пост", callback_data="admin_task_type:reaction")],
        [InlineKeyboardButton(text="🤖 Запуск бота", callback_data="admin_task_type:start_bot")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
    await callback.message.edit_text("➕ *Создание задания (админ)*\n\nВыбери тип:", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(CreateTaskStates.choosing_type)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_task_type:"))
async def cb_admin_task_type(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    task_type = callback.data.split(":")[1]
    await state.update_data(task_type=task_type)
    await callback.message.edit_text("Отправь ссылку:")
    await state.set_state(CreateTaskStates.entering_link)
    await callback.answer()


@router.callback_query(F.data == "admin_create_special")
async def cb_admin_create_special(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("⭐️ *Особое задание*\n\nВведи описание задания (что должен сделать пользователь):", parse_mode="Markdown")
    await state.set_state(AdminStates.special_task_description)
    await callback.answer()


@router.message(AdminStates.special_task_description)
async def msg_special_task_description(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    description = message.text.strip()
    await state.update_data(special_description=description)
    await message.answer(f"✅ Описание: {description}\n\nВведи награду за исполнителя (мин. 100 токенов):")
    await state.set_state(AdminStates.special_task_reward)


@router.message(AdminStates.special_task_reward)
async def msg_special_task_reward(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        reward = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    if reward < 100:
        await message.answer("⚠️ Минимум 100 токенов!")
        return
    data = await state.get_data()
    description = data['special_description']
    await message.answer(f"✅ Награда: {reward}\n\nВведи общий бюджет задания:")
    await state.update_data(special_reward=reward)
    await state.set_state(AdminStates.entering_budget)


@router.message(AdminStates.entering_budget)
async def msg_special_budget(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        budget = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    data = await state.get_data()
    reward = data['special_reward']
    description = data['special_description']
    if budget < reward:
        await message.answer(f"⚠️ Бюджет должен быть не меньше {reward}!")
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT balance FROM users WHERE telegram_id = ?', (message.from_user.id,))
        user = await cursor.fetchone()
        balance = user[0]
    if balance < budget:
        await message.answer(f"⚠️ Недостаточно токенов! Баланс: {balance}, нужно: {budget}")
        return
    max_executors = budget // reward
    remainder = budget - (max_executors * reward)
    await state.update_data(budget=budget, max_executors=max_executors, remainder=remainder)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_special_task")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
    await message.answer(
        f"📋 *Сводка:*\n\nОписание: {description}\nНаграда: {reward}\nБюджет: {budget}\nМакс. исполнителей: {max_executors}\nВернётся: {remainder}\n\nПодтвердить?",
        reply_markup=kb, parse_mode="Markdown"
    )
    await state.set_state(CreateTaskStates.confirming)


@router.callback_query(F.data == "confirm_special_task", CreateTaskStates.confirming)
async def cb_confirm_special_task(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    data = await state.get_data()
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('''
            INSERT INTO tasks (creator_id, task_type, link, reward, budget, max_executors, completed_count, status, description)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'active', ?)
        ''', (callback.from_user.id, 'special', 'special_task', data['special_reward'], data['budget'], data['max_executors'], data['special_description']))
        await db.execute('UPDATE users SET balance = balance - ? WHERE telegram_id = ?', (data['budget'], callback.from_user.id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (callback.from_user.id, -data['budget'], 'task_create', 'Создание особого задания')
        )
        await db.commit()
    await state.clear()
    await callback.message.edit_text("✅ Особое задание создано! Пользователи будут отправлять отчёты на твою проверку.")
    await callback.answer()


@router.callback_query(F.data == "admin_delete_task")
async def cb_admin_delete_task(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "🗑 *Удаление задания*\n\n"
        "Введи ID задания для удаления.\n"
        "Админ может удалять любые задания.\n"
        "Пользователю вернутся неиспользованные токены.",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.delete_task_id)
    await callback.answer()


@router.message(AdminStates.delete_task_id)
async def msg_admin_delete_task(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        task_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число (ID задания)!")
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute(
            'SELECT id, creator_id, budget, reward, completed_count, max_executors, status FROM tasks WHERE id = ?',
            (task_id,)
        )
        task = await cursor.fetchone()
        if not task:
            await message.answer("❌ Задание не найдено!")
            await state.clear()
            return
        t_id, creator_id, budget, reward, completed, max_exec, status = task
        if status not in ['active', 'reported']:
            await message.answer(f"⚠️ Задание уже в статусе '{status}', удалять нечего.")
            await state.clear()
            return
        refund = budget - (completed * reward)
        await db.execute("UPDATE tasks SET status = 'deleted' WHERE id = ?", (task_id,))
        if refund > 0:
            await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (refund, creator_id))
            await db.execute(
                'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                (creator_id, refund, 'task_delete_refund', f'Возврат токенов при удалении задания #{task_id} админом')
            )
        await db.commit()
    await state.clear()
    await message.answer(
        f"✅ Задание #{task_id} удалено!\n"
        f"Создатель (ID {creator_id}): выполнено {completed}/{max_exec}\n"
        f"Возвращено токенов: {refund}"
    )


@router.callback_query(F.data == "admin_delete_all_tasks")
async def cb_admin_delete_all_tasks(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'active'")
        count = (await cursor.fetchone())[0]
    if count == 0:
        await callback.message.edit_text("📋 Нет активных заданий для удаления.")
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, УДАЛИТЬ ВСЕ", callback_data="confirm_delete_all_tasks")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(
        f"⚠️ *ВНИМАНИЕ!*\n\n"
        f"Ты собираешься удалить **ВСЕ** активные задания ({count} шт.).\n\n"
        f"Пользователям будут возвращены неиспользованные токены.\n\n"
        f"Это действие нельзя отменить!\n\n"
        f"Нажми кнопку для подтверждения:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_all_tasks")
async def cb_confirm_delete_all_tasks(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute("SELECT id, creator_id, budget, reward, completed_count FROM tasks WHERE status = 'active'")
        tasks = await cursor.fetchall()
        total_count = len(tasks)
        total_refund = 0
        for task in tasks:
            task_id, creator_id, budget, reward, completed = task
            refund = budget - (completed * reward)
            await db.execute("UPDATE tasks SET status = 'deleted' WHERE id = ?", (task_id,))
            if refund > 0:
                await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (refund, creator_id))
                await db.execute(
                    'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                    (creator_id, refund, 'task_delete_refund', f'Возврат токенов при массовом удалении заданий (задание #{task_id})')
                )
                total_refund += refund
        await db.commit()
    await callback.message.edit_text(
        f"✅ Удалено заданий: {total_count}\n"
        f"💰 Возвращено токенов пользователям: {total_refund}"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_premium")
async def cb_admin_add_premium(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("👑 Введи username пользователя (без @):")
    await state.set_state(AdminStates.add_premium_username)
    await callback.answer()


@router.message(AdminStates.add_premium_username)
async def msg_admin_add_premium_username(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    username = message.text.strip().lstrip('@')
    await state.update_data(target_username=username)
    await message.answer(f"Username: @{username}\n\nВведи количество дней премиума:")
    await state.set_state(AdminStates.add_premium_days)


@router.message(AdminStates.add_premium_days)
async def msg_admin_add_premium_days(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    data = await state.get_data()
    username = data['target_username']
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT telegram_id FROM users WHERE username = ?', (username,))
        user = await cursor.fetchone()
        if not user:
            await message.answer("❌ Пользователь не найден!")
            await state.clear()
            return
        user_id = user[0]
        expires_at = (datetime.now() + timedelta(days=days)).isoformat()
        await db.execute('UPDATE users SET is_premium = 1, premium_expires_at = ? WHERE telegram_id = ?', (expires_at, user_id))
        await db.commit()
    expires = datetime.fromisoformat(expires_at)
    await state.clear()
    await message.answer(f"✅ Премиум выдан @{username} на {days} дней!\nДо: {escape_md(expires.strftime('%d.%m.%Y %H:%M'))}")


@router.callback_query(F.data == "admin_ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("🚫 Введи Telegram ID пользователя:")
    await state.set_state(AdminStates.ban_user)
    await callback.answer()


@router.message(AdminStates.ban_user)
async def msg_admin_ban(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT username FROM users WHERE telegram_id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            await message.answer("❌ Пользователь не найден!")
            return
        await db.execute('UPDATE users SET is_banned = 1 WHERE telegram_id = ?', (user_id,))
        await db.commit()
    await state.clear()
    await message.answer(f"✅ Пользователь @{escape_md(user[0] or '')} (ID: {user_id}) заблокирован!")


@router.callback_query(F.data == "admin_unban")
async def cb_admin_unban(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("✅ Введи Telegram ID пользователя:")
    await state.set_state(AdminStates.unban_user)
    await callback.answer()


@router.message(AdminStates.unban_user)
async def msg_admin_unban(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT username FROM users WHERE telegram_id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            await message.answer("❌ Пользователь не найден!")
            return
        await db.execute('UPDATE users SET is_banned = 0 WHERE telegram_id = ?', (user_id,))
        await db.commit()
    await state.clear()
    await message.answer(f"✅ Пользователь @{escape_md(user[0] or '')} (ID: {user_id}) разблокирован!")


@router.callback_query(F.data == "admin_create_promo")
async def cb_admin_create_promo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("🎁 Введи код промокода:")
    await state.set_state(AdminStates.create_promo)
    await callback.answer()


@router.message(AdminStates.create_promo)
async def msg_admin_create_promo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    promo_code = message.text.strip().upper()
    await state.update_data(promo_code=promo_code)
    await message.answer(f"Код: {promo_code}\n\nВведи количество токенов:")
    await state.set_state(AdminStates.create_promo_amount)


@router.message(AdminStates.create_promo_amount)
async def msg_admin_create_promo_amount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    await state.update_data(promo_amount=amount)
    await message.answer(f"Сумма: {amount}\n\nВведи максимальное количество использований:")
    await state.set_state(AdminStates.create_promo_uses)


@router.message(AdminStates.create_promo_uses)
async def msg_admin_create_promo_uses(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        max_uses = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    data = await state.get_data()
    promo_code = data['promo_code']
    amount = data['promo_amount']
    async with aiosqlite.connect('bot_database.db') as db:
        try:
            await db.execute('INSERT INTO promo_codes (code, amount, max_uses) VALUES (?, ?, ?)', (promo_code, amount, max_uses))
            await db.commit()
        except aiosqlite.IntegrityError:
            await message.answer("❌ Промокод уже существует!")
            await state.clear()
            return
    await state.clear()
    await message.answer(f"✅ Промокод создан!\n\nКод: {promo_code}\nСумма: {amount}\nИспользований: {max_uses}")


@router.callback_query(F.data == "admin_delete_promo")
async def cb_admin_delete_promo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("❌ Введи код промокода:")
    await state.set_state(AdminStates.delete_promo)
    await callback.answer()


@router.message(AdminStates.delete_promo)
async def msg_admin_delete_promo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    promo_code = message.text.strip().upper()
    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('SELECT id FROM promo_codes WHERE code = ?', (promo_code,))
        promo = await cursor.fetchone()
        if not promo:
            await message.answer("❌ Промокод не найден!")
            return
        await db.execute('DELETE FROM promo_codes WHERE code = ?', (promo_code,))
        await db.commit()
    await state.clear()
    await message.answer(f"✅ Промокод {promo_code} удален!")


@router.callback_query(F.data == "admin_add_tokens")
async def cb_admin_add_tokens(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("💰 Введи ID или username пользователя:")
    await state.set_state(AdminStates.add_tokens_username)
    await callback.answer()


@router.message(AdminStates.add_tokens_username)
async def msg_admin_add_tokens_username(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    search_value = message.text.strip().lstrip('@')
    await state.update_data(target_search=search_value)
    if search_value.isdigit():
        await message.answer(f"🔍 ID: {search_value}\n\nВведи количество токенов:")
    else:
        await message.answer(f"🔍 @{search_value}\n\nВведи количество токенов:")
    await state.set_state(AdminStates.add_tokens_amount)


@router.message(AdminStates.add_tokens_amount)
async def msg_admin_add_tokens_amount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    data = await state.get_data()
    search_value = data['target_search']
    async with aiosqlite.connect('bot_database.db') as db:
        if search_value.isdigit():
            cursor = await db.execute('SELECT telegram_id, username, balance FROM users WHERE telegram_id = ?', (int(search_value),))
        else:
            cursor = await db.execute('SELECT telegram_id, username, balance FROM users WHERE username = ?', (search_value,))
        user = await cursor.fetchone()
        if not user:
            await message.answer("❌ Пользователь не найден!")
            await state.clear()
            return
        user_id, username, current_balance = user
        username_display = f"@{escape_md(username)}" if username else f"ID {user_id}"
        await db.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (amount, user_id))
        await db.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (user_id, amount, 'admin_add', f'Админ начислил {amount} токенов')
        )
        await db.commit()
    await state.clear()
    await message.answer(f"✅ Начислено {amount} токенов {username_display}!\nНовый баланс: {current_balance + amount}")


# --- ЗАПУСК ---
async def main():
    await init_db()
    await start_scheduler()
    await start_monthly_top_scheduler()
    print("🚀 База данных инициализирована. Бот запущен!")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
