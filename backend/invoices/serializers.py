from rest_framework import serializers

from .field_template import FIELD_KEYS, ORIGIN_CHOICES
from .models import InvoiceImage, InvoiceRecord

LINE_ITEM_ORIGINS = ('auto', 'manual', 'empty')


class InvoiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceImage
        fields = ['id', 'local_read_status', 'server_status', 'created_at']


class InvoiceImageDetailSerializer(serializers.ModelSerializer):
    data_uri = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceImage
        fields = ['id', 'local_read_status', 'server_status', 'server_ocr_text', 'data_uri', 'created_at']

    def get_data_uri(self, obj):
        return f'data:{obj.content_type};base64,{obj.image_data}'


class InvoiceRecordSerializer(serializers.ModelSerializer):
    images = InvoiceImageSerializer(many=True, read_only=True)

    class Meta:
        model = InvoiceRecord
        fields = ['id', 'created_at', 'updated_at', 'fields', 'line_items', 'has_pending_server_review', 'notified', 'images']


class InvoiceRecordCreateSerializer(serializers.Serializer):
    fields = serializers.DictField()
    line_items = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    images = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate_fields(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('fields must be an object keyed by field name.')
        unknown = set(value.keys()) - FIELD_KEYS
        if unknown:
            raise serializers.ValidationError(f'Unknown field keys: {sorted(unknown)}')

        normalized = {}
        for key in FIELD_KEYS:
            entry = value.get(key) or {}
            origin = entry.get('origin', 'empty')
            if origin not in ORIGIN_CHOICES:
                raise serializers.ValidationError(f'Invalid origin "{origin}" for field "{key}".')
            confidence = entry.get('confidence')
            normalized[key] = {
                'value': entry.get('value') or '',
                'origin': origin,
                'confidence': float(confidence) if confidence is not None else None,
            }
        return normalized

    def validate_images(self, value):
        cleaned = []
        for image in value:
            if not image.get('image_data'):
                raise serializers.ValidationError('Each image requires base64 image_data.')
            local_read_status = image.get('local_read_status', 'ok')
            if local_read_status not in ('ok', 'unreadable'):
                raise serializers.ValidationError('local_read_status must be "ok" or "unreadable".')
            cleaned.append({
                'image_data': image['image_data'],
                'content_type': image.get('content_type') or 'image/jpeg',
                'local_read_status': local_read_status,
            })
        return cleaned

    def validate_line_items(self, value):
        cleaned = []
        for item in value:
            origin = item.get('origin', 'manual')
            if origin not in LINE_ITEM_ORIGINS:
                origin = 'manual'
            cleaned.append({
                'description': item.get('description') or '',
                'quantity': item.get('quantity') or '',
                'unit_price': item.get('unit_price') or '',
                'amount': item.get('amount') or '',
                'origin': origin,
            })
        return cleaned

    def create(self, validated_data):
        request = self.context['request']
        images_data = validated_data.pop('images', [])
        has_unreadable = any(image['local_read_status'] == 'unreadable' for image in images_data)

        fields = validated_data['fields']
        for key in FIELD_KEYS:
            field = fields[key]
            if field['value'] == '' and field['origin'] == 'empty' and has_unreadable:
                field['origin'] = 'server-pending'

        user = getattr(request, 'user', None)
        record = InvoiceRecord.objects.create(
            created_by=user if user and user.is_authenticated else None,
            fields=fields,
            line_items=validated_data.get('line_items', []),
            has_pending_server_review=has_unreadable,
        )
        for image in images_data:
            InvoiceImage.objects.create(
                record=record,
                image_data=image['image_data'],
                content_type=image['content_type'],
                local_read_status=image['local_read_status'],
                server_status='pending' if image['local_read_status'] == 'unreadable' else 'not_needed',
            )
        return record
