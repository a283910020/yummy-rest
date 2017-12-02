"""The API routes"""
import sys
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash
from flask import jsonify, request, make_response
from flask_restplus import Resource
from flask_jwt import jwt, jwt_required

from app import APP
from .restplus import API
from .models import db, User, BlacklistToken
from .serializers import add_user, login_user
from .parsers import auth_header

user_ns = API.namespace('users', description="User administration operations.")
auth_ns = API.namespace('auth', description="Authentication/Authorization operations.")

# token decode function:
def decode_access_token(access_token):
        """
        Validates the user access token
        :param access_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(access_token, APP.config.get('SECRET_KEY'))
            is_blacklisted_token = BlacklistToken.check_blacklisted(access_token)
            if is_blacklisted_token:
                return 'Token blacklisted. Please log in again.'
            else:
                public_id = payload['sub']
                user = User.query.filter_by(public_id=public_id).first()
                return user.id
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'

@user_ns.route('/')
class GeneralUserHandler(Resource):
    def get(self):
        """
        Returns all the users in the database
        """

        users = User.query.all()
        if users:
            output = []
            for user in users:
                user_data = {}
                user_data['email'] = user.email
                user_data['password'] = user.password
                user_data['public_id'] = user.public_id
                user_data['username'] = user.username
                output.append(user_data)
            return jsonify({"users": output})
        return jsonify({"message": "No user(s) added!"})

@user_ns.route('/<public_id>')
class SpecificUserHandler(Resource):
    
    def get(self, public_id):
        """
        Gets a single user to admin
        """
        user = User.query.filter_by(public_id=public_id).first()
        print(user, file=sys.stdout)
        if not user:
            print(user, file=sys.stdout)
            resp_object = jsonify({"message": "No user found!"})
            return make_response(resp_object), 204

        user_data = {}
        user_data['email'] = user.email
        user_data['password'] = user.password
        user_data['public_id'] = user.public_id
        user_data['username'] = user.username
        return make_response(jsonify({"user": user_data}), 200)
    

    def delete(self, public_id):
        """
        Removes a user account
        """
        user = User.query.filter_by(public_id=public_id).first()

        if not user:
            return make_response(jsonify({"message": "No user found!"})), 204

        db.session.delete(user)
        db.session.commit()

        return make_response(jsonify({"message": "User was deleted!"}), 200)

@auth_ns.route('/register')
class RegisterHandler(Resource):
    """
    This class handles user account creation.
    """

    @API.expect(add_user)
    def post(self):
        """
        Registers a new user account.
        """
        data = request.get_json()

        # Check if user exists
        user = User.query.filter_by(email=data['email']).first()
        if not user:
            try:
                new_user = User(email=data['email'], username=data['username'], password=data['password'])
                db.session.add(new_user)
                db.session.commit()
                return make_response(jsonify({'message': 'Registered successfully!'}), 201)
            except Exception as e: # pragma: no cover
                response = {"message": "Some error occured. Please retry."}
                return make_response(jsonify(response), 501)
        else:
            return make_response(jsonify({'message': 'User already exists. Please Log in instead.'}), 202)

@auth_ns.route('/login')
class LoginHandler(Resource):
    """
    This class handles user login
    """

    @API.expect(login_user)
    def post(self):
        """
        User Login/SignIn route
        """
        login_info = request.get_json()
        if not login_info: # pragma: no cover
            return make_response(jsonify({'message': 'Input payload validation failed'}), 401)
        try:
            user = User.query.filter_by(email=login_info['email']).first()
            if not user:
                return make_response(jsonify({"message": 'User does not exist!'}), 404)
            if check_password_hash(user.password, login_info['password']):
                payload = {
                    'exp':  datetime.utcnow() + timedelta(minutes=30),
                    'iat': datetime.utcnow(),
                    'sub': user.public_id
                }
                token = jwt.encode(
                    payload,
                    APP.config['SECRET_KEY'],
                    algorithm='HS256'
                )
                return jsonify({"message": "Logged in successfully.",
                                "access_token": token.decode('UTF-8')
                               })
            return make_response(jsonify({"message": "Incorrect credentials."}), 401)
        except exec as e: # pragma: no cover
            print(e)
            return make_response(jsonify({"message": "An error occurred. Please try again."}), 501)

@auth_ns.route('/logout')
class LogoutHandler(Resource):
    """
    This class handles user logout
    """

    @API.expect(auth_header, validate=True)
    def post(self):
        """
        Logout route
        """
        access_token = request.headers.get('access_token')
        print(access_token, file=sys.stdout)
        if access_token:
            result = decode_access_token(access_token)
            print(result, file=sys.stdout)
            if not isinstance(result, str):
                # mark the token as blacklisted
                blacklisted_token = BlacklistToken(access_token)
                print(blacklisted_token, file=sys.stdout)
                try:
                    # insert the token
                    db.session.add(blacklisted_token)
                    db.session.commit()
                    response_obj = dict(
                        status="success",
                        message="Logged out successfully."
                    )
                    print(jsonify(response_obj), file=sys.stdout)
                    return make_response(jsonify(response_obj), 200)
                except Exception as e:
                    resp_obj = {
                        'status': 'fail',
                        'message': e
                    }
                    return make_response(jsonify(resp_obj), 200)
            else:
                resp_obj = dict(
                    status="fail",
                    message=result
                )
                print(jsonify(resp_obj), file=sys.stdout)
                return make_response(jsonify(resp_obj), 401)
        else:
            response_obj = {
                'status': 'fail',
                'message': 'Provide a valid auth token.'
            }
            return make_response(jsonify(response_obj), 403)

# ADD the namespaces created to the API
API.add_namespace(auth_ns)
API.add_namespace(user_ns)
API.init_app(APP)
