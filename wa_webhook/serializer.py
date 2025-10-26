from rest_framework import serializers
import re

class wa_text_message_sr(serializers.Serializer):
    text = serializers.CharField(max_length=2000)
    to = serializers.IntegerField()
    
    def validate_to(self, value):
        print("validate ### valida ",value)
        pattern = r'^(?:20|0)?(10|11|12|15)[0-9]{8}$'
        if not re.match(pattern, str(value)):
            raise serializers.ValidationError("Invalid Egyptian mobile number format.")
        return value

   