from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Task

User = get_user_model()

DEMO_PASSWORD = "demo12345"

TASKS = (
    ("Revisar contrato do cliente", "Ler o aditivo e apontar riscos.", "in_progress", 2, "demo"),
    ("Fechar relatório mensal", "Consolidar números de outubro.", "todo", 5, "demo"),
    ("Subir correção do checkout", "Hotfix validado em staging.", "done", -1, "demo"),
    ("Planejar sprint 24", "Refinamento com o time na quinta.", "todo", 9, "maria"),
    ("Atualizar documentação da API", "Schema e exemplos de erro.", "in_progress", -2, "maria"),
    ("Revisar PR de autenticação", "Foco em expiração de token.", "todo", 1, "demo"),
    ("Preparar demo para o cliente", "Roteiro de 10 minutos.", "todo", 3, "maria"),
    ("Corrigir filtro de datas", "Fuso horário no filtro de vencimento.", "done", -4, "demo"),
    ("Migrar job de e-mail para Celery", "Remover thread manual.", "in_progress", 6, "demo"),
    ("Escrever testes de permissão", "Cobrir dono, responsável e intruso.", "todo", None, "maria"),
)


class Command(BaseCommand):
    help = "Cria usuários e tarefas de demonstração (idempotente)."

    def handle(self, *args, **options):
        demo, _ = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@blt.local", "first_name": "Demo", "last_name": "User"},
        )
        demo.set_password(DEMO_PASSWORD)
        demo.save()

        maria, _ = User.objects.get_or_create(
            username="maria",
            defaults={"email": "maria@blt.local", "first_name": "Maria", "last_name": "Souza"},
        )
        maria.set_password(DEMO_PASSWORD)
        maria.save()

        users = {"demo": demo, "maria": maria}
        today = timezone.localdate()
        created = 0
        for title, description, status, due_offset, assignee in TASKS:
            due_date = today + timedelta(days=due_offset) if due_offset is not None else None
            _, was_created = Task.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "status": status,
                    "due_date": due_date,
                    "assigned_to": users[assignee],
                    "created_by": demo,
                    "completed_at": timezone.now() if status == Task.Status.DONE else None,
                },
            )
            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed pronto: {created} tarefa(s) criada(s). "
                f"Login: demo / {DEMO_PASSWORD} (e maria / {DEMO_PASSWORD})"
            )
        )
