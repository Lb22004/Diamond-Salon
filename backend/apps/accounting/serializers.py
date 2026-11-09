from decimal import Decimal

from rest_framework import serializers

from apps.accounting.models import Account, AccountMapping, JournalEntry, JournalEntryLine


class AccountSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(required=False)
    parent_code = serializers.CharField(source="parent.code", read_only=True, default=None)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    level_label = serializers.CharField(read_only=True)
    account_type_label = serializers.CharField(source="get_account_type_display", read_only=True)
    nature_label = serializers.CharField(source="get_nature_display", read_only=True)
    inventory_type_label = serializers.CharField(
        source="get_inventory_type_display", read_only=True, default=None
    )
    has_movements = serializers.BooleanField(read_only=True, default=False)
    debit_total = serializers.CharField(read_only=True, default="0.00")
    credit_total = serializers.CharField(read_only=True, default="0.00")
    balance = serializers.CharField(read_only=True, default="0.00")

    class Meta:
        model = Account
        fields = [
            "id",
            "code",
            "name",
            "parent",
            "parent_code",
            "parent_name",
            "level",
            "level_label",
            "account_type",
            "account_type_label",
            "nature",
            "nature_label",
            "classification",
            "accepts_entries",
            "inventory_type",
            "inventory_type_label",
            "niif_reference",
            "debit_rule",
            "credit_rule",
            "is_active",
            "has_movements",
            "debit_total",
            "credit_total",
            "balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "parent_code",
            "parent_name",
            "level_label",
            "account_type_label",
            "nature_label",
            "inventory_type_label",
            "has_movements",
            "debit_total",
            "credit_total",
            "balance",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance: Account | None = self.instance
        code = (attrs.get("code", instance.code if instance else "") or "").strip()
        parent = attrs.get("parent", instance.parent if instance else None)
        level = attrs.get("level", instance.level if instance else None)
        account_type = attrs.get("account_type", instance.account_type if instance else None)
        nature = attrs.get("nature", instance.nature if instance else None)
        accepts_entries = attrs.get(
            "accepts_entries", instance.accepts_entries if instance else False
        )

        # RF-CAT-05: Lock code, nature, account_type, and parent once the account has movements
        if instance is not None:
            has_moves = JournalEntryLine.objects.filter(account=instance).exists()
            if has_moves:
                if "code" in attrs and attrs["code"] != instance.code:
                    raise serializers.ValidationError(
                        {"code": "El código no puede modificarse porque la cuenta ya registra movimientos (RF-CAT-05)."}
                    )
                if "nature" in attrs and attrs["nature"] != instance.nature:
                    raise serializers.ValidationError(
                        {"nature": "La naturaleza no puede modificarse porque la cuenta ya registra movimientos (RF-CAT-05)."}
                    )
                if "parent" in attrs and attrs["parent"] != instance.parent:
                    raise serializers.ValidationError(
                        {"parent": "La cuenta padre no puede modificarse porque la cuenta ya registra movimientos (RF-CAT-05)."}
                    )
                if "accepts_entries" in attrs and not attrs["accepts_entries"]:
                    raise serializers.ValidationError(
                        {"accepts_entries": "Una cuenta con movimientos no puede dejar de ser analítica (RF-CAT-04)."}
                    )

            if instance.children.exists() and accepts_entries:
                raise serializers.ValidationError(
                    {"accepts_entries": "Una cuenta agrupadora con subcuentas hijas no puede aceptar movimientos directos (RF-CAT-04)."}
                )

        # RF-CAT-02 & RF-CAT-04: Parent/child hierarchy rules
        if parent is None:
            if level is None:
                attrs["level"] = 1
                level = 1
            if level != 1:
                raise serializers.ValidationError(
                    {"level": "Las cuentas sin cuenta padre deben ser de Nivel 1 (Clase)."}
                )
        else:
            if instance and parent.pk == instance.pk:
                raise serializers.ValidationError({"parent": "Una cuenta no puede ser padre de sí misma."})

            # RF-CAT-04: An account that has movements cannot become a parent
            if JournalEntryLine.objects.filter(account=parent).exists():
                raise serializers.ValidationError(
                    {
                        "parent": f"La cuenta {parent.code} ({parent.name}) ya tiene movimientos contables y no puede convertirse en cuenta agrupadora (RF-CAT-04)."
                    }
                )

            if not code.startswith(parent.code) or code == parent.code:
                raise serializers.ValidationError(
                    {
                        "code": f"El código de la subcuenta ({code}) debe iniciar con el código de su cuenta padre ({parent.code}) (RF-CAT-02)."
                    }
                )

            expected_level = parent.level + 1
            if level is None:
                attrs["level"] = expected_level
            elif level != expected_level:
                attrs["level"] = expected_level

            if not account_type:
                attrs["account_type"] = parent.account_type
            if not nature:
                attrs["nature"] = parent.nature

        return attrs


class AccountMappingSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = AccountMapping
        fields = ["key", "account", "account_code", "account_name", "description"]
        read_only_fields = ["key", "account_code", "account_name"]

    def validate_account(self, account: Account):
        if not account.is_active or not account.accepts_entries:
            raise serializers.ValidationError(
                f"La cuenta {account.code} ({account.name}) debe estar activa y ser analítica (aceptar movimientos)."
            )
        return account


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_nature = serializers.CharField(source="account.nature", read_only=True)

    class Meta:
        model = JournalEntryLine
        fields = [
            "id",
            "line_no",
            "account",
            "account_code",
            "account_name",
            "account_nature",
            "description",
            "debit",
            "credit",
        ]
        read_only_fields = ["id", "account_code", "account_name", "account_nature"]


class JournalEntrySerializer(serializers.ModelSerializer):
    period_label = serializers.CharField(source="period.label", read_only=True)
    period_code = serializers.CharField(source="period.code", read_only=True)
    entry_type_label = serializers.CharField(source="get_entry_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    posted_by_username = serializers.CharField(
        source="posted_by.username", read_only=True, default=None
    )
    reversal_of_number = serializers.IntegerField(
        source="reversal_of.entry_number", read_only=True, default=None
    )
    reversed_by_id = serializers.IntegerField(
        source="reversed_by.id", read_only=True, default=None
    )
    reversed_by_number = serializers.IntegerField(
        source="reversed_by.entry_number", read_only=True, default=None
    )
    source_link = serializers.SerializerMethodField()
    lines = JournalEntryLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "period",
            "period_label",
            "period_code",
            "entry_number",
            "entry_date",
            "description",
            "entry_type",
            "entry_type_label",
            "source_app",
            "source_id",
            "source_link",
            "status",
            "status_label",
            "reversal_of",
            "reversal_of_number",
            "reversed_by_id",
            "reversed_by_number",
            "total_debit",
            "total_credit",
            "created_by",
            "created_by_username",
            "posted_by",
            "posted_by_username",
            "posted_at",
            "created_at",
            "lines",
        ]
        read_only_fields = fields

    def get_source_link(self, obj: JournalEntry) -> str | None:
        if not obj.source_app:
            return None
        app = obj.source_app.lower()
        if "sales" in app:
            return f"/libro-ventas?source_id={obj.source_id or ''}"
        if "purchases" in app:
            return f"/libro-compras?source_id={obj.source_id or ''}"
        if "inventory" in app:
            return f"/inventario?source_id={obj.source_id or ''}"
        return None


class JournalEntryLineWriteSerializer(serializers.Serializer):
    account = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    debit = serializers.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit = serializers.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))


class JournalEntryWriteSerializer(serializers.Serializer):
    entry_date = serializers.DateField()
    description = serializers.CharField()
    entry_type = serializers.ChoiceField(
        choices=JournalEntry.EntryType.choices,
        default=JournalEntry.EntryType.MANUAL,
        required=False,
    )
    post_now = serializers.BooleanField(default=False, required=False)
    lines = JournalEntryLineWriteSerializer(many=True)
