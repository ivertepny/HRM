from django.core.management.base import BaseCommand, CommandError

from apps.slack import client
from apps.slack.reminders import remind_attendance, remind_pending_vacations


class Command(BaseCommand):
    help = (
        "Щоденні нагадування в Slack: --attendance (хто ще не відмітився в табелі "
        "сьогодні; лише в робочі дні), --vacations (заявки, що чекають розгляду). "
        "Запускає cron; повторний запуск того ж дня не дублює повідомлень."
    )

    def add_arguments(self, parser):
        parser.add_argument("--attendance", action="store_true")
        parser.add_argument("--vacations", action="store_true")

    def handle(self, *args, attendance, vacations, **options):
        if not (attendance or vacations):
            raise CommandError("Вкажіть --attendance і/або --vacations.")
        if not client.enabled():
            self.stdout.write("SLACK_BOT_TOKEN не задано — нагадування вимкнені.")
            return
        if attendance:
            self.stdout.write(f"Табель: надіслано {remind_attendance()}.")
        if vacations:
            self.stdout.write(f"Відпустки: надіслано {remind_pending_vacations()}.")
