from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Item, Category
from .serializers import ItemSerializer, CategorySerializer, UserSerializer


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_root(request):
    return Response({
        "message": "Welcome to the API",
        "endpoints": {
            "items": "/api/items/",
            "categories": "/api/categories/",
            "login": "/api/auth/login/",
            "register": "/api/auth/register/",
            "logout": "/api/auth/logout/",
            "me": "/api/auth/me/",
        }
    })


# ─── Auth endpoints (no CSRF, no session dependency) ─────────────────────────

@api_view(['POST'])
@authentication_classes([])          # skip JWT/Session entirely
@permission_classes([permissions.AllowAny])
def user_register(request):
    """Create a new user account and return their info."""
    serializer = UserSerializer(data=request.data)
    if not serializer.is_valid():
        first_error = next(iter(serializer.errors.values()))[0]
        return Response({'error': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    role_label = _get_role(user)
    return Response({
        'message': 'Account created successfully',
        'user': _user_payload(user, role_label)
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([])          # skip JWT/Session entirely → no CSRF check
@permission_classes([permissions.AllowAny])
def user_login(request):
    """Authenticate and return user info stored in localStorage on the frontend."""
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    selected_role = request.data.get('role', 'user')

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=400)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Incorrect username or password'}, status=400)

    # Validate the selected role matches the user's actual permissions
    if selected_role == 'admin' and not user.is_superuser:
        return Response({'error': 'You do not have Admin privileges'}, status=403)
    if selected_role == 'staff' and not (user.is_staff or getattr(user, 'is_moderator', False) or user.is_superuser):
        return Response({'error': 'You do not have Staff privileges'}, status=403)

    role_label = _get_role(user)
    return Response({
        'message': f'Welcome back, {user.username}!',
        'user': _user_payload(user, role_label)
    })


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def user_logout(request):
    """Frontend-only logout — just returns success so the client can clear localStorage."""
    return Response({'message': 'Logged out successfully'})


@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def user_me(request):
    """
    The frontend passes the saved username as a query param to refresh user info.
    e.g. GET /api/auth/me/?username=john
    """
    username = request.query_params.get('username')
    if not username:
        return Response({'error': 'username param required'}, status=400)
    try:
        user = User.objects.get(username=username)
        return Response({'user': _user_payload(user, _get_role(user))})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


# ─── Helper functions ─────────────────────────────────────────────────────────

def _get_role(user):
    if user.is_superuser:
        return 'admin'
    if user.is_staff or getattr(user, 'is_moderator', False):
        return 'staff'
    return 'user'


def _user_payload(user, role_label):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': role_label,
        'is_moderator': getattr(user, 'is_moderator', False),
        'is_superuser': user.is_superuser,
    }


# ─── Item & Category ViewSets ─────────────────────────────────────────────────

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    authentication_classes = []

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('-created_at')
    serializer_class = ItemSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']
    authentication_classes = []   # no CSRF enforcement
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_permissions(self):
        if self.action in ['destroy', 'update', 'partial_update']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()

        # If the requester identifies as moderator (via localStorage role header),
        # only allow quantity edits
        requester_role = request.headers.get('X-User-Role', 'user')
        if requester_role == 'staff':
            data = {'quantity': data.get('quantity', instance.quantity)}

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


# Keep the old ViewSet registered at /api/users/ for backwards compat
class UserRegisterView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        return user_register(request._request)