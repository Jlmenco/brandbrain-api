"""Seed script — populates database with sample data for development.

Usage: python -m app.scripts.seed
"""

import random
from datetime import datetime, timedelta
from datetime import date as date_type

from sqlmodel import Session

from app.database import engine, create_db_and_tables
from app.models.user import User, OrgMember
from app.models.organization import Organization
from app.models.cost_center import CostCenter
from app.models.influencer import Influencer, BrandKit
from app.models.content import MacroContent, ContentItem
from app.models.campaign import Campaign
from app.models.tracking import Lead
from app.models.market import MarketSource, Competitor
from app.models.metrics import MetricsDaily
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.services.auth_service import hash_password


def _generate_metrics(db: Session, content_item_id: str, posted_at: datetime, days: int = 30):
    """Gera metricas diarias simuladas para um conteudo publicado."""
    start = posted_at.date() if isinstance(posted_at, datetime) else posted_at
    today = date_type.today()
    for i in range(days):
        day = start + timedelta(days=i)
        if day > today:
            break
        decay = max(0.1, 1.0 - (i / days) * 0.7)
        base_impressions = random.randint(800, 3000)
        db.add(MetricsDaily(
            content_item_id=content_item_id,
            date=day,
            impressions=int(base_impressions * decay),
            likes=int(base_impressions * decay * random.uniform(0.03, 0.08)),
            comments=int(base_impressions * decay * random.uniform(0.005, 0.02)),
            shares=int(base_impressions * decay * random.uniform(0.002, 0.01)),
            clicks=int(base_impressions * decay * random.uniform(0.02, 0.06)),
            followers_delta=random.randint(0, 8),
        ))


def seed():
    create_db_and_tables()

    with Session(engine) as db:
        # Check if already seeded
        from sqlmodel import select
        existing = db.exec(select(User).where(User.email == "admin@brandbrain.dev")).first()
        if existing:
            print("Database already seeded. Skipping.")
            return

        random.seed(42)
        now = datetime.utcnow()
        print("Seeding database...")

        # --- Users ---
        admin = User(
            email="admin@brandbrain.dev",
            name="Admin",
            hashed_password=hash_password("admin123"),
        )
        editor = User(
            email="editor@brandbrain.dev",
            name="Editor",
            hashed_password=hash_password("editor123"),
        )
        viewer = User(
            email="viewer@brandbrain.dev",
            name="Viewer",
            hashed_password=hash_password("viewer123"),
        )
        db.add_all([admin, editor, viewer])
        db.flush()

        # --- Organization ---
        org = Organization(name="Grupo JLM")
        db.add(org)
        db.flush()

        # --- Members ---
        db.add(OrgMember(org_id=org.id, user_id=admin.id, role="owner"))
        db.add(OrgMember(org_id=org.id, user_id=editor.id, role="editor"))
        db.add(OrgMember(org_id=org.id, user_id=viewer.id, role="viewer"))
        db.flush()

        # --- Cost Centers ---
        cc_melpura = CostCenter(
            org_id=org.id,
            name="Melpura",
            code="MELPURA",
            monthly_budget_media=5000.0,
            monthly_budget_ai=500.0,
        )
        cc_meat = CostCenter(
            org_id=org.id,
            name="MeatFriends",
            code="MEATFRIENDS",
            monthly_budget_media=8000.0,
            monthly_budget_ai=800.0,
        )
        db.add_all([cc_melpura, cc_meat])
        db.flush()

        # --- Influencer Master ---
        master = Influencer(
            org_id=org.id,
            cost_center_id=None,
            type="master",
            name="Voz do Grupo JLM",
            niche="agronegócio e tecnologia",
            tone="autoridade, consultivo, claro, sem exageros",
            emoji_level="none",
            forbidden_topics=["política", "religião"],
            forbidden_words=["garantido", "milagre", "100%"],
            cta_style="CTA leve (comentário, salvar, visitar link)",
            language="pt-BR",
        )
        db.add(master)
        db.flush()

        db.add(BrandKit(
            influencer_id=master.id,
            description="Voz institucional do Grupo JLM",
            value_props={"qualidade": True, "rastreabilidade": True, "tecnologia": True},
            products={"grupo": "Grupo JLM", "marcas": ["Melpura", "MeatFriends"]},
            audience={"perfil": "empresários, produtores rurais, consumidores conscientes"},
        ))

        # --- Influencer Melpura ---
        inf_mel = Influencer(
            org_id=org.id,
            cost_center_id=cc_melpura.id,
            type="brand",
            name="Mel Expert",
            niche="mel natural e apicultura",
            tone="acolhedor, educativo, próximo",
            emoji_level="medium",
            forbidden_topics=["política", "religião"],
            forbidden_words=["garantido", "milagre"],
            allowed_words=["mel puro", "natural", "apiário"],
            cta_style="Salve para lembrar! / Já experimentou?",
            language="pt-BR",
        )
        db.add(inf_mel)
        db.flush()

        db.add(BrandKit(
            influencer_id=inf_mel.id,
            description="Influencer digital da Melpura",
            value_props={"pureza": True, "rastreabilidade": True, "sabor": True},
            products={"mel_silvestre": "Mel silvestre 500g", "mel_orgânico": "Mel orgânico 300g"},
            audience={"perfil": "consumidores de produtos naturais, 25-45 anos"},
            links={"site": "https://melpura.com.br", "instagram": "@melpura"},
        ))

        # --- Influencer MeatFriends ---
        inf_meat = Influencer(
            org_id=org.id,
            cost_center_id=cc_meat.id,
            type="brand",
            name="Meat Guru",
            niche="carnes premium e churrasco",
            tone="descontraído, expert, premium",
            emoji_level="low",
            forbidden_topics=["política", "religião", "veganismo"],
            forbidden_words=["garantido", "milagre", "barato"],
            allowed_words=["premium", "maturado", "rastreável"],
            cta_style="Marque um amigo churrasqueiro!",
            language="pt-BR",
        )
        db.add(inf_meat)
        db.flush()

        db.add(BrandKit(
            influencer_id=inf_meat.id,
            description="Influencer digital da MeatFriends",
            value_props={"qualidade": True, "rastreabilidade": True, "premium": True},
            products={"picanha": "Picanha Angus Premium", "costela": "Costela Window"},
            audience={"perfil": "amantes de churrasco, 30-55 anos, classe A/B"},
            links={"site": "https://meatfriends.com.br", "instagram": "@meatfriends"},
        ))

        # --- Macro Content ---
        macro = MacroContent(
            org_id=org.id,
            influencer_master_id=master.id,
            theme="Rastreabilidade: o futuro da confiança alimentar",
            content_raw="A rastreabilidade é o que diferencia marcas sérias no mercado alimentar. "
                        "Quando você sabe de onde vem o que consome, a confiança cresce. "
                        "No Grupo JLM, cada produto tem história — e você pode acompanhar.",
            content_structured={
                "hook": "Você sabe de onde vem o que consome?",
                "body": "A rastreabilidade é o diferencial...",
                "cta": "Conheça mais sobre nosso processo.",
            },
            status="ready",
        )
        db.add(macro)
        db.flush()

        # --- Content Items: Melpura ---
        ci_mel_draft = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            source_macro_id=macro.id,
            provider_target="instagram",
            text="Você sabia que nosso mel é rastreável do apiário até sua mesa? "
                 "Cada pote tem QR code para você conhecer a origem. "
                 "Porque transparência é o melhor ingrediente! 🍯\n\n"
                 "#MelPuro #Rastreabilidade #Melpura #MelNatural",
            status="draft",
        )
        ci_mel_review = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            source_macro_id=macro.id,
            provider_target="instagram",
            text="O mel é um dos alimentos mais puros da natureza. "
                 "Rico em antioxidantes, antibacteriano natural e fonte de energia rápida. "
                 "Inclua na sua rotina e sinta a diferença! 🐝✨\n\n"
                 "#Melpura #MelNatural #SaudeNatural #BemEstar",
            status="review",
        )
        ci_mel_approved = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            provider_target="linkedin",
            text="Produção sustentável não é apenas uma escolha — é um compromisso. "
                 "Na Melpura, trabalhamos com apicultores que respeitam o ciclo natural das abelhas. "
                 "O resultado? Um mel com sabor autêntico e consciência ambiental.\n\n"
                 "#Sustentabilidade #Melpura #Apicultura",
            status="approved",
        )
        ci_mel_scheduled = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            provider_target="instagram",
            text="3 receitas fáceis com mel natural para o seu café da manhã:\n\n"
                 "1. Panqueca com mel e frutas vermelhas\n"
                 "2. Iogurte com granola e fio de mel\n"
                 "3. Torrada com cream cheese e mel\n\n"
                 "Salve para não esquecer! 🍯📌\n\n"
                 "#Melpura #ReceitasComMel #CafeDaManha",
            status="scheduled",
            scheduled_at=now + timedelta(days=2),
        )
        ci_mel_posted_1 = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            source_macro_id=macro.id,
            provider_target="instagram",
            text="Agora ficou ainda mais fácil saber de onde vem o seu mel! 📱\n\n"
                 "Cada pote Melpura tem um QR code exclusivo. "
                 "Escaneie e acompanhe toda a jornada: do apiário até a sua casa.\n\n"
                 "Transparência que você pode ver. 🍯\n\n"
                 "#Melpura #QRCode #Rastreabilidade #MelPuro",
            status="posted",
            posted_at=now - timedelta(days=15),
            provider_post_id="demo-mel-001",
            provider_post_url="https://demo.brandbrain.dev/post/mel-001",
        )
        ci_mel_posted_2 = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            provider_target="linkedin",
            text="Case de sucesso: como nossa parceria com apicultores familiares "
                 "transformou a produção de mel no interior de São Paulo.\n\n"
                 "Mais de 50 famílias impactadas, 200% de aumento na produtividade "
                 "e um mel de qualidade certificada.\n\n"
                 "#Melpura #ImpactoSocial #Apicultura #CaseDeSuccesso",
            status="posted",
            posted_at=now - timedelta(days=8),
            provider_post_id="demo-mel-002",
            provider_post_url="https://demo.brandbrain.dev/post/mel-002",
        )
        ci_mel_posted_3 = ContentItem(
            cost_center_id=cc_melpura.id,
            influencer_id=inf_mel.id,
            provider_target="instagram",
            text="Dia Mundial das Abelhas! 🐝🌍\n\n"
                 "Sem elas, 75% das culturas alimentares do planeta seriam comprometidas. "
                 "Na Melpura, cuidar das abelhas é cuidar do futuro.\n\n"
                 "O que você pode fazer? Plante flores, evite agrotóxicos "
                 "e consuma mel de produtores responsáveis.\n\n"
                 "#DiaMundialDasAbelhas #Melpura #SalveAsAbelhas",
            status="posted",
            posted_at=now - timedelta(days=22),
            provider_post_id="demo-mel-003",
            provider_post_url="https://demo.brandbrain.dev/post/mel-003",
        )

        # --- Content Items: MeatFriends ---
        ci_meat_review = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            source_macro_id=macro.id,
            provider_target="linkedin",
            text="Rastreabilidade não é tendência — é obrigação para quem leva carne a sério. "
                 "Na MeatFriends, cada corte tem certificação de origem e maturação controlada. "
                 "Porque confiança se constrói com transparência.\n\n"
                 "#MeatFriends #CarnesPremium #Rastreabilidade",
            status="review",
        )
        ci_meat_draft = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            provider_target="instagram",
            text="5 dicas para o preparo perfeito da picanha:\n\n"
                 "1. Retire da geladeira 30 min antes\n"
                 "2. Sal grosso generoso na capa de gordura\n"
                 "3. Grelha bem quente — sele rápido\n"
                 "4. Descanse 5 min antes de fatiar\n"
                 "5. Fatias contra a fibra, sempre!\n\n"
                 "Marque aquele amigo churrasqueiro! 🔥🥩\n\n"
                 "#MeatFriends #Picanha #DicasDeChurrasco",
            status="draft",
        )
        ci_meat_approved = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            provider_target="linkedin",
            text="A rastreabilidade na cadeia de carnes é mais do que um diferencial — "
                 "é uma responsabilidade com o consumidor.\n\n"
                 "Na MeatFriends, cada corte carrega informações sobre origem, "
                 "alimentação do animal, tempo de maturação e certificações.\n\n"
                 "Isso é carne premium de verdade.\n\n"
                 "#MeatFriends #Rastreabilidade #CarnePremium",
            status="approved",
        )
        ci_meat_scheduled = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            provider_target="instagram",
            text="Fim de semana chegando e a MeatFriends preparou algo especial! 🎉🥩\n\n"
                 "Kit Churrasco Premium com 20% de desconto:\n"
                 "- Picanha Angus\n"
                 "- Costela Window\n"
                 "- Linguiça artesanal\n\n"
                 "Apenas neste fim de semana. Link na bio!\n\n"
                 "#MeatFriends #Promocao #ChurrascoPremium",
            status="scheduled",
            scheduled_at=now + timedelta(days=3),
        )
        ci_meat_posted_1 = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            provider_target="instagram",
            text="Churrasco premium começa com a escolha certa. 🔥\n\n"
                 "Nossa Picanha Angus tem maturação controlada de 21 dias — "
                 "o resultado é uma carne macia, suculenta e com sabor incomparável.\n\n"
                 "Já experimentou? O paladar agradece. 🥩\n\n"
                 "#MeatFriends #PicanhaAngus #ChurrascoPremium",
            status="posted",
            posted_at=now - timedelta(days=12),
            provider_post_id="demo-meat-001",
            provider_post_url="https://demo.brandbrain.dev/post/meat-001",
        )
        ci_meat_posted_2 = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            provider_target="linkedin",
            text="Sustentabilidade na pecuária: como a MeatFriends está redefinindo "
                 "o padrão da indústria.\n\n"
                 "Parceria com produtores certificados, rastreabilidade completa "
                 "e compromisso com o bem-estar animal.\n\n"
                 "O consumidor premium quer mais do que sabor — quer consciência.\n\n"
                 "#MeatFriends #Sustentabilidade #PecuariaResponsavel",
            status="posted",
            posted_at=now - timedelta(days=5),
            provider_post_id="demo-meat-002",
            provider_post_url="https://demo.brandbrain.dev/post/meat-002",
        )
        ci_meat_posted_3 = ContentItem(
            cost_center_id=cc_meat.id,
            influencer_id=inf_meat.id,
            provider_target="instagram",
            text="Lançamento: Costela Window MeatFriends! 🥩🎉\n\n"
                 "Corte premium com maturação especial, "
                 "perfeito para aquele churrasco inesquecível.\n\n"
                 "Disponível em lojas selecionadas. "
                 "Confira no link da bio!\n\n"
                 "#MeatFriends #CostelaWindow #Lancamento #CarnePremium",
            status="posted",
            posted_at=now - timedelta(days=20),
            provider_post_id="demo-meat-003",
            provider_post_url="https://demo.brandbrain.dev/post/meat-003",
        )

        db.add_all([
            ci_mel_draft, ci_mel_review, ci_mel_approved, ci_mel_scheduled,
            ci_mel_posted_1, ci_mel_posted_2, ci_mel_posted_3,
            ci_meat_review, ci_meat_draft, ci_meat_approved, ci_meat_scheduled,
            ci_meat_posted_1, ci_meat_posted_2, ci_meat_posted_3,
        ])
        db.flush()

        # --- Metrics for posted items ---
        posted_items = [
            ci_mel_posted_1, ci_mel_posted_2, ci_mel_posted_3,
            ci_meat_posted_1, ci_meat_posted_2, ci_meat_posted_3,
        ]
        for item in posted_items:
            _generate_metrics(db, item.id, item.posted_at)

        # --- Audit Logs ---
        def _audit(actor_id, action, target_id, cc_id, days_ago, meta=None):
            db.add(AuditLog(
                org_id=org.id,
                cost_center_id=cc_id,
                actor_user_id=actor_id,
                action=action,
                target_type="content_item",
                target_id=target_id,
                metadata_json=meta or {},
                created_at=now - timedelta(days=days_ago, hours=random.randint(0, 12)),
            ))

        # Posted items: full workflow (create → submit_review → approve → schedule → publish_now)
        for ci in posted_items:
            days_posted = (now - ci.posted_at).days
            _audit(editor.id, "create", ci.id, ci.cost_center_id, days_posted + 4)
            _audit(editor.id, "submit_review", ci.id, ci.cost_center_id, days_posted + 3)
            _audit(admin.id, "approve", ci.id, ci.cost_center_id, days_posted + 2)
            _audit(admin.id, "schedule", ci.id, ci.cost_center_id, days_posted + 1, {"scheduled_at": str(ci.posted_at)})
            _audit(admin.id, "publish_now", ci.id, ci.cost_center_id, days_posted)

        # Scheduled items: create → submit → approve → schedule
        for ci in [ci_mel_scheduled, ci_meat_scheduled]:
            _audit(editor.id, "create", ci.id, ci.cost_center_id, 5)
            _audit(editor.id, "submit_review", ci.id, ci.cost_center_id, 4)
            _audit(admin.id, "approve", ci.id, ci.cost_center_id, 3)
            _audit(admin.id, "schedule", ci.id, ci.cost_center_id, 2, {"scheduled_at": str(ci.scheduled_at)})

        # Approved items: create → submit → approve
        for ci in [ci_mel_approved, ci_meat_approved]:
            _audit(editor.id, "create", ci.id, ci.cost_center_id, 6)
            _audit(editor.id, "submit_review", ci.id, ci.cost_center_id, 5)
            _audit(admin.id, "approve", ci.id, ci.cost_center_id, 4)

        # Review items: create → submit
        for ci in [ci_mel_review, ci_meat_review]:
            _audit(editor.id, "create", ci.id, ci.cost_center_id, 3)
            _audit(editor.id, "submit_review", ci.id, ci.cost_center_id, 2)

        # Draft items: just create
        for ci in [ci_mel_draft, ci_meat_draft]:
            _audit(editor.id, "create", ci.id, ci.cost_center_id, 1)

        db.flush()

        # --- Notifications ---
        def _notif(user_id, title, body, target_id, days_ago, is_read=False):
            db.add(Notification(
                org_id=org.id,
                user_id=user_id,
                type="status_change",
                title=title,
                body=body[:100],
                target_type="content_item",
                target_id=target_id,
                is_read=is_read,
                email_sent=True,
                created_at=now - timedelta(days=days_ago, hours=random.randint(1, 10)),
            ))

        # Notificacoes para admin (conteudos enviados para revisao)
        _notif(admin.id, "Conteudo enviado para revisao", ci_mel_review.text, ci_mel_review.id, 2)
        _notif(admin.id, "Conteudo enviado para revisao", ci_meat_review.text, ci_meat_review.id, 2)
        _notif(admin.id, "Conteudo enviado para revisao", ci_mel_approved.text, ci_mel_approved.id, 5, is_read=True)
        _notif(admin.id, "Conteudo enviado para revisao", ci_meat_approved.text, ci_meat_approved.id, 5, is_read=True)

        # Notificacoes para editor (conteudos aprovados/agendados)
        _notif(editor.id, "Conteudo aprovado", ci_mel_approved.text, ci_mel_approved.id, 4, is_read=True)
        _notif(editor.id, "Conteudo aprovado", ci_meat_approved.text, ci_meat_approved.id, 4, is_read=True)
        _notif(editor.id, "Conteudo agendado", ci_mel_scheduled.text, ci_mel_scheduled.id, 2)
        _notif(editor.id, "Conteudo agendado", ci_meat_scheduled.text, ci_meat_scheduled.id, 2)
        _notif(editor.id, "Conteudo publicado", ci_mel_posted_1.text, ci_mel_posted_1.id, 15, is_read=True)
        _notif(editor.id, "Conteudo publicado", ci_meat_posted_1.text, ci_meat_posted_1.id, 12, is_read=True)

        # Notificacoes para viewer (conteudos publicados)
        _notif(viewer.id, "Conteudo publicado", ci_mel_posted_1.text, ci_mel_posted_1.id, 15, is_read=True)
        _notif(viewer.id, "Conteudo publicado", ci_meat_posted_2.text, ci_meat_posted_2.id, 5)

        db.flush()

        # --- Campaigns ---
        camp_mel_1 = Campaign(
            cost_center_id=cc_melpura.id,
            name="Lançamento Mel Orgânico",
            objective="leads",
            start_date=date_type.today() - timedelta(days=30),
            end_date=date_type.today() + timedelta(days=30),
        )
        camp_mel_2 = Campaign(
            cost_center_id=cc_melpura.id,
            name="Black Friday Mel",
            objective="traffic",
            start_date=date_type.today() + timedelta(days=60),
            end_date=date_type.today() + timedelta(days=75),
        )
        camp_meat_1 = Campaign(
            cost_center_id=cc_meat.id,
            name="Campanha Verão Churrasco",
            objective="awareness",
            start_date=date_type.today() - timedelta(days=15),
            end_date=date_type.today() + timedelta(days=45),
        )
        camp_meat_2 = Campaign(
            cost_center_id=cc_meat.id,
            name="Programa Fidelidade",
            objective="leads",
            start_date=date_type.today() - timedelta(days=60),
        )
        db.add_all([camp_mel_1, camp_mel_2, camp_meat_1, camp_meat_2])
        db.flush()

        # Vincular alguns content items a campanhas
        ci_mel_posted_1.campaign_id = camp_mel_1.id
        ci_mel_posted_2.campaign_id = camp_mel_1.id
        ci_mel_scheduled.campaign_id = camp_mel_1.id
        ci_meat_posted_1.campaign_id = camp_meat_1.id
        ci_meat_posted_2.campaign_id = camp_meat_1.id
        ci_meat_scheduled.campaign_id = camp_meat_1.id
        db.add_all([ci_mel_posted_1, ci_mel_posted_2, ci_mel_scheduled,
                     ci_meat_posted_1, ci_meat_posted_2, ci_meat_scheduled])

        # --- Leads ---
        db.add_all([
            Lead(cost_center_id=cc_melpura.id, source="form", name="Ana Silva", email="ana@email.com", phone="11999001122", score=80, status="qualified"),
            Lead(cost_center_id=cc_melpura.id, source="whatsapp", name="Carlos Mendes", email="carlos@email.com", phone="11988112233", score=60, status="new"),
            Lead(cost_center_id=cc_melpura.id, source="form", name="Lucia Ferreira", email="lucia@email.com", phone="11977223344", score=95, status="won"),
            Lead(cost_center_id=cc_melpura.id, source="dm", name="Pedro Santos", email="pedro@email.com", phone="11966334455", score=30, status="new"),
            Lead(cost_center_id=cc_meat.id, source="manual", name="Ricardo Oliveira", email="ricardo@email.com", phone="11955445566", score=70, status="qualified"),
            Lead(cost_center_id=cc_meat.id, source="dm", name="Fernanda Costa", email="fernanda@email.com", phone="11944556677", score=45, status="new"),
            Lead(cost_center_id=cc_meat.id, source="whatsapp", name="Marcos Almeida", email="marcos@email.com", phone="11933667788", score=85, status="won"),
            Lead(cost_center_id=cc_meat.id, source="form", name="Julia Ribeiro", email="julia@email.com", phone="11922778899", score=20, status="lost"),
        ])

        # --- Market Sources ---
        db.add(MarketSource(
            org_id=org.id,
            cost_center_id=None,
            name="Google Trends Brasil",
            type="trends",
            url="https://trends.google.com.br",
            tags=["tendências", "busca", "brasil"],
        ))
        db.add(MarketSource(
            org_id=org.id,
            cost_center_id=cc_melpura.id,
            name="ABEMEL - Associação Brasileira de Mel",
            type="rss",
            url="https://abemel.com.br",
            tags=["mel", "apicultura", "setor"],
        ))

        # --- Competitors ---
        db.add(Competitor(
            org_id=org.id,
            cost_center_id=cc_melpura.id,
            name="Mel Flores do Campo",
            website_url="https://example.com",
            notes="Referência em conteúdo educativo sobre mel",
        ))
        db.add(Competitor(
            org_id=org.id,
            cost_center_id=cc_meat.id,
            name="Friboi Premium",
            website_url="https://example.com",
            notes="Líder em marketing de carnes premium",
        ))

        db.commit()

        # --- Embed Brand Kits (RAG) ---
        from app.services.embedding_service import get_embedding_service
        emb_svc = get_embedding_service()
        total_chunks = 0
        for inf_id in [master.id, inf_mel.id, inf_meat.id]:
            count = emb_svc.embed_brand_kit(db, inf_id)
            total_chunks += count
        db.commit()

        print("Seed completed successfully!")
        print(f"  Organization: {org.name} ({org.id})")
        print(f"  Admin:  admin@brandbrain.dev / admin123 (owner)")
        print(f"  Editor: editor@brandbrain.dev / editor123 (editor)")
        print(f"  Viewer: viewer@brandbrain.dev / viewer123 (viewer)")
        print(f"  Cost Centers: Melpura ({cc_melpura.id}), MeatFriends ({cc_meat.id})")
        print(f"  Influencers: Master ({master.id}), Mel Expert ({inf_mel.id}), Meat Guru ({inf_meat.id})")
        print(f"  Content Items: 14 total (draft/review/approved/scheduled/posted)")
        print(f"  Metrics: ~{len(posted_items) * 30} daily records for posted items")
        print(f"  Audit Logs: workflow history for all content items")
        print(f"  Notifications: demo notifications for admin, editor, viewer")
        print(f"  Brand Kit Embeddings: {total_chunks} chunks embedded (RAG)")


if __name__ == "__main__":
    seed()
