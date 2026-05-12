from rest_framework import serializers
from .models import Item, Category
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class ItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), 
        source='category', 
        write_only=True, 
        required=False
    )
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = ['id', 'title', 'description', 'quantity', 'price', 'category', 'category_id', 'image', 'image_url', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[('user', 'User'), ('staff', 'Staff'), ('admin', 'Admin')], write_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'is_moderator']
        extra_kwargs = {
            'is_moderator': {'read_only': True}
        }
    
    def create(self, validated_data):
        role = validated_data.pop('role')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        
        # Set role-based permissions
        if role == 'admin':
            user.is_superuser = True
            user.is_staff = True
            user.is_moderator = True
        elif role == 'staff':
            user.is_superuser = False
            user.is_staff = True
            user.is_moderator = True
        else: # user
            user.is_superuser = False
            user.is_staff = False
            user.is_moderator = False
            
        user.save()
        return user