from django.core.management.base import BaseCommand

from trivia_app.services.trivia_retention import delete_expired_trivia_questions


class Command(BaseCommand):
    help = 'Delete expired trivia questions and answers while retaining cycle and trophy history.'

    def handle(self, *args, **options):
        deleted_count = delete_expired_trivia_questions()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_count} expired trivia records.'))
