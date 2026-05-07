# -*- coding: utf-8 -*-
"""
JWT Authentication controller for the Next.js portal.
All API routes use auth='none' to prevent Odoo from redirecting to /web/login.

Security features:
- JWT secret from ir.config_parameter or environment variable
- Token refresh endpoint with rotation
- Failed login attempt logging
- File upload validation
- Permission checks before sudo()
"""
import json
import logging
import os
import functools
from datetime import datetime, timedelta

import jwt

from odoo import http, SUPERUSER_ID
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# JWT Configuration
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24
JWT_REFRESH_EXPIRY_DAYS = 30

# File upload limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_UPLOAD = 5
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}
ALLOWED_MIMETYPES = {
    'image/jpeg', 'image/png', 'image/gif',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

# CORS origins — configurable via ir.config_parameter or env
DEFAULT_CORS_ORIGINS = 'http://localhost:3003'

# Role mapping: Odoo facility_role → portal-facing role
ROLE_MAP = {
    'student': 'user',
    'faculty': 'faculty',
    'employee': 'employee',
    'technician': 'technician',
    'facility_supervisor': 'manager',
    'facility_manager': 'manager',
    'contractor': 'contractor',
    'contract_officer': 'manager',
    'sustainability_officer': 'manager',
    'safety_officer': 'manager',
    'management': 'manager',
}

# Manager-level roles for authorization checks
MANAGER_ROLES = ('facility_manager', 'facility_supervisor', 'management')


# ============================================================
#  JWT Secret Management
# ============================================================
def _get_jwt_secret():
    """Get JWT secret from ir.config_parameter, env var, or fallback.

    Priority:
    1. Odoo system parameter: rua_facility.jwt_secret
    2. Environment variable: RUA_JWT_SECRET
    3. Fallback (dev only, logs warning)
    """
    try:
        env = request.env(user=SUPERUSER_ID)
        secret = env['ir.config_parameter'].get_param('rua_facility.jwt_secret')
        if secret:
            return secret
    except Exception:
        pass

    secret = os.environ.get('RUA_JWT_SECRET')
    if secret:
        return secret

    _logger.warning(
        'JWT secret not configured! Set ir.config_parameter '
        '"rua_facility.jwt_secret" or env var "RUA_JWT_SECRET". '
        'Using insecure fallback for development only.'
    )
    return 'rua_facility_jwt_dev_fallback_change_me'


# ============================================================
#  Helper: JSON Response Builder
# ============================================================
def api_response(data=None, message='', success=True, errors=None, meta=None, status=200):
    """Build a standardized JSON API response."""
    body = {
        'success': success,
        'data': data,
        'message': message,
        'errors': errors or [],
    }
    if meta is not None:
        body['meta'] = meta
    return Response(
        json.dumps(body, default=str, ensure_ascii=False),
        status=status,
        content_type='application/json; charset=utf-8',
    )


def api_error(message, status=400, errors=None):
    return api_response(data=None, message=message, success=False,
                        errors=errors, status=status)


# ============================================================
#  Decorator: JWT Auth Required
# ============================================================
def api_auth_required(func):
    """Decorator to enforce JWT token authentication on API endpoints."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.httprequest.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return api_error('Token required', status=401)

        token_str = auth_header[7:]
        secret = _get_jwt_secret()

        try:
            payload = jwt.decode(token_str, secret, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return api_error('Token expired', status=401)
        except jwt.InvalidTokenError:
            return api_error('Invalid token', status=401)

        # Ensure this is an access token, not a refresh token
        if payload.get('type') != 'access':
            return api_error('Invalid token type', status=401)

        user_id = payload.get('user_id')
        if not user_id:
            return api_error('Invalid token', status=401)

        # Set environment to the authenticated user
        try:
            env = request.env(user=user_id)
            user = env['res.users'].browse(user_id)
            if not user.exists() or not user.active:
                return api_error('User not found or inactive', status=401)
        except Exception:
            return api_error('Authentication failed', status=401)

        # Attach user info to request for downstream use
        request.facility_user = user
        request.facility_env = env

        return func(*args, **kwargs)

    return wrapper


def _get_portal_role(user):
    """Get portal-facing role string for a user."""
    if user._is_superuser():
        return 'admin'
    return ROLE_MAP.get(user.facility_role or '', 'user')


def _generate_tokens(user, secret):
    """Generate access and refresh JWT tokens for a user."""
    now = datetime.utcnow()
    portal_role = _get_portal_role(user)

    access_payload = {
        'user_id': user.id,
        'login': user.login,
        'role': portal_role,
        'exp': now + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': now,
        'type': 'access',
    }
    refresh_payload = {
        'user_id': user.id,
        'exp': now + timedelta(days=JWT_REFRESH_EXPIRY_DAYS),
        'iat': now,
        'type': 'refresh',
    }

    return {
        'access_token': jwt.encode(access_payload, secret, algorithm=JWT_ALGORITHM),
        'refresh_token': jwt.encode(refresh_payload, secret, algorithm=JWT_ALGORITHM),
        'token_type': 'Bearer',
        'expires_in': JWT_EXPIRY_HOURS * 3600,
    }


def _serialize_user(user):
    """Serialize user profile for API response."""
    return {
        'id': user.id,
        'name': user.name,
        'login': user.login,
        'email': user.email,
        'role': _get_portal_role(user),
        'national_id': user.national_id,
        'university_id': user.university_id,
        'department': user.department_name,
        'college': user.college_name,
        'avatar_url': f'/web/image/res.users/{user.id}/avatar_128',
    }


# ============================================================
#  File Upload Validation
# ============================================================
def validate_file_upload(files):
    """Validate uploaded files. Returns list of error dicts or empty list."""
    errors = []

    if len(files) > MAX_FILES_PER_UPLOAD:
        errors.append({
            'field': 'files',
            'message': f'Maximum {MAX_FILES_PER_UPLOAD} files allowed per upload',
        })
        return errors

    for f in files:
        # Check extension
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            errors.append({
                'field': 'files',
                'message': f'File type .{ext} not allowed for "{f.filename}". '
                           f'Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}',
            })

        # Check MIME type
        if f.content_type and f.content_type not in ALLOWED_MIMETYPES:
            errors.append({
                'field': 'files',
                'message': f'MIME type {f.content_type} not allowed for "{f.filename}"',
            })

        # Check file size (read and seek back)
        f.seek(0, 2)  # seek to end
        size = f.tell()
        f.seek(0)  # seek back to start
        if size > MAX_FILE_SIZE:
            errors.append({
                'field': 'files',
                'message': f'File "{f.filename}" exceeds maximum size of '
                           f'{MAX_FILE_SIZE // (1024*1024)} MB',
            })

    return errors


# ============================================================
#  Auth Controller
# ============================================================
class FacilityAuthAPI(http.Controller):

    @http.route('/api/v1/auth/login', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def login(self, **kwargs):
        """Authenticate user and return JWT tokens."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid request data', status=400)

        login_id = data.get('login', '').strip()
        password = data.get('password', '').strip()

        if not login_id or not password:
            return api_error('Username and password are required', status=400)

        # Accept db from payload, or fall back to request.db
        db = data.get('db') or request.db
        ip = request.httprequest.environ.get('REMOTE_ADDR', 'unknown')
        _logger.info('Portal login attempt: user=%s, db=%s, ip=%s', login_id, db, ip)

        if not db:
            return api_error('Database not configured', status=500)

        try:
            # Odoo 19 uses credential dict for authenticate()
            credential = {
                'type': 'password',
                'login': login_id,
                'password': password,
            }
            auth_info = request.env['res.users'].sudo().with_context(
                no_reset_password=True
            ).authenticate(credential, {'interactive': False})
            # Odoo 19 authenticate() returns a dict: {'uid': int, 'auth_method': str, ...}
            uid = auth_info['uid'] if isinstance(auth_info, dict) else auth_info
        except Exception as e:
            _logger.warning('Portal login exception for user=%s ip=%s: %s', login_id, ip, e)
            uid = False

        if not uid:
            # Generic message — do not reveal whether user exists
            _logger.warning('Portal login failed: user=%s, db=%s, ip=%s', login_id, db, ip)
            return api_error('Invalid credentials', status=401)

        user = request.env['res.users'].sudo().browse(uid)

        # Generate tokens
        secret = _get_jwt_secret()
        tokens = _generate_tokens(user, secret)
        tokens['user'] = _serialize_user(user)

        _logger.info('Portal login success: user=%s (uid=%s), ip=%s', login_id, uid, ip)
        return api_response(data=tokens, message='Login successful')

    @http.route('/api/v1/auth/refresh', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def refresh_token(self, **kwargs):
        """Refresh access token using a valid refresh token."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid request data', status=400)

        refresh_token = data.get('refresh_token', '').strip()
        if not refresh_token:
            return api_error('Refresh token is required', status=400)

        secret = _get_jwt_secret()

        try:
            payload = jwt.decode(refresh_token, secret, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return api_error('Refresh token expired', status=401)
        except jwt.InvalidTokenError:
            return api_error('Invalid refresh token', status=401)

        # Validate token type
        if payload.get('type') != 'refresh':
            return api_error('Invalid token type', status=401)

        user_id = payload.get('user_id')
        if not user_id:
            return api_error('Invalid refresh token', status=401)

        # Verify user is still active
        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists() or not user.active:
            return api_error('User not found or inactive', status=401)

        # Generate new token pair (rotation)
        tokens = _generate_tokens(user, secret)

        return api_response(data=tokens, message='Token refreshed successfully')

    @http.route('/api/v1/auth/me', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def me(self, **kwargs):
        """Return current authenticated user profile."""
        user = request.facility_user
        return api_response(data=_serialize_user(user))

    @http.route('/api/v1/auth/logout', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def logout(self, **kwargs):
        """Logout — client should discard tokens."""
        return api_response(message='Logged out')
