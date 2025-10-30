# AquaCharge Backend Authentication System

## 🔐 **Complete Authentication API Endpoints**

### **Base URL**: `/api/auth`

### **Endpoints Implemented**

#### 1. **Login** - `POST /api/auth/login`
- **Purpose**: Authenticate user credentials and return JWT token
- **Body**: `{ "email": "user@example.com", "password": "password123" }`
- **Response**: JWT token, user data, expiry time
- **Features**:
  - Email case-insensitive matching
  - Password verification using SHA-256
  - User active status check
  - JWT token generation with 24-hour expiry

#### 2. **Register** - `POST /api/auth/register`
- **Purpose**: Create new user account
- **Body**: `{ "displayName": "user123", "email": "user@example.com", "password": "password123" }`
- **Response**: JWT token and user data (auto-login)
- **Features**:
  - Email and displayName uniqueness validation
  - Email format validation
  - Password strength validation (8+ chars, letters + numbers)
  - Automatic role assignment (USER)

#### 3. **Verify Token** - `POST /api/auth/verify-token`
- **Purpose**: Validate JWT token and return user data
- **Headers**: `Authorization: Bearer <token>`
- **Response**: User data and validation status
- **Features**:
  - Token expiry validation
  - User active status check
  - Role information included

#### 4. **Refresh Token** - `POST /api/auth/refresh`
- **Purpose**: Generate new JWT token from existing (even expired) token
- **Headers**: `Authorization: Bearer <token>`
- **Response**: New JWT token with fresh expiry
- **Features**:
  - Accepts expired tokens for refresh
  - User validation before issuing new token

#### 5. **Forgot Password** - `POST /api/auth/forgot-password`
- **Purpose**: Initiate password reset process
- **Body**: `{ "email": "user@example.com" }`
- **Response**: Success message (always, to prevent email enumeration)
- **Features**:
  - Secure token generation
  - 2-hour token expiry
  - Email enumeration protection

#### 6. **Reset Password** - `POST /api/auth/reset-password`
- **Purpose**: Reset password using reset token
- **Body**: `{ "token": "reset_token", "new_password": "newpassword123" }`
- **Response**: Success confirmation
- **Features**:
  - Token validation and expiry check
  - One-time use tokens
  - Password strength validation

#### 7. **Change Password** - `POST /api/auth/change-password`
- **Purpose**: Change password for authenticated user
- **Headers**: `Authorization: Bearer <token>`
- **Body**: `{ "current_password": "old", "new_password": "new123" }`
- **Response**: Success confirmation
- **Features**:
  - Current password verification
  - New password different from current
  - Password strength validation

#### 8. **Get Current User** - `GET /api/auth/me`
- **Purpose**: Get current authenticated user data
- **Headers**: `Authorization: Bearer <token>`
- **Response**: Complete user profile
- **Features**:
  - Token validation
  - Role name included
  - Excludes sensitive data

#### 9. **Logout** - `POST /api/auth/logout`
- **Purpose**: Logout user (client-side token removal)
- **Response**: Success message
- **Note**: JWT tokens are stateless; actual logout handled client-side

## 🛡️ **Security Features**

### **Password Security**
- SHA-256 password hashing
- Password strength validation (8+ chars, letters + numbers)
- Current password verification for changes

### **JWT Token Security**
- 24-hour token expiry
- Secure secret key configuration
- Role-based payload
- Refresh token capability

### **API Security**
- Input validation and sanitization
- Email enumeration protection
- Rate limiting ready (middleware can be added)
- Error handling without information disclosure

### **Authentication Middleware**
- `@require_auth` decorator for protected routes
- `@require_role` decorator for role-based access
- Request context user injection

## 📁 **Files Created**

```
backend/
├── api/
│   └── auth.py              # Main authentication endpoints
├── middleware/
│   └── auth.py              # Authentication decorators/middleware
├── test/
│   └── testAuth.py          # Comprehensive authentication tests
├── config.py                # Configuration management
└── requirements.txt         # Updated with PyJWT dependency
```

## 🧪 **Testing**

### **Test Coverage**
- ✅ Login success/failure scenarios
- ✅ Registration validation
- ✅ Token verification
- ✅ Password reset flow
- ✅ Password change functionality
- ✅ Authentication middleware
- ✅ Error handling

### **Run Tests**
```bash
cd backend
pytest test/testAuth.py -v
```

## 🔧 **Configuration**

### **Environment Variables** (Production)
```bash
JWT_SECRET_KEY=your-super-secure-secret-key
SECRET_KEY=flask-secret-key
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### **Demo Credentials**
- **Admin**: admin@aquacharge.com / admin123
- **Operator**: operator@blueharbor.com / operator456
- **User**: captain@oceanbreezes.com / user789

## 🚀 **Integration Ready**

The authentication system is fully integrated with:
- ✅ Existing user management system
- ✅ Frontend authentication context
- ✅ Role-based access control
- ✅ Sample data and demo accounts
- ✅ Comprehensive error handling

## 🔄 **Frontend Integration**

The frontend `AuthContext` is already configured to work with these endpoints:
- Login: `/api/auth/login`
- Register: `/api/auth/register` 
- Token verification: `/api/auth/verify-token`
- User data: `/api/auth/me`

## 📦 **Dependencies Added**
- `PyJWT==2.8.0` - JWT token handling

The authentication system is production-ready with proper security measures, comprehensive testing, and seamless integration with the existing AquaCharge platform!