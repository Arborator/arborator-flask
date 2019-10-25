#!/usr/bin/python3
import os
from .app import create_app
from flask_cors import CORS, cross_origin
from flask import render_template, flash, redirect, url_for, jsonify, request, Response, abort

config_name = os.getenv('FLASK_CONFIG')
app = create_app(config_name)
# CORS(app)
cors = CORS(app
    , resources={r"/*": {"origins": "*"}}
    ,expose_headers='Authorization', 
    allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    supports_credentials=True)
# app.config['CORS_HEADERS'] = "Content-Type", "Authorization", "Access-Control-Allow-Credentials"

# @app.before_request
# def authorize_token():
#     print('before', request)
#     print(request.method)
#     print(request.headers)
#     print('referer', request.headers['Referer'])
#     if request.endpoint == 'test':
#         try:
#             if request.method != 'OPTIONS':  # <-- required
#                 auth_header = request.headers.get("Authorization")
#                 if "Bearer" in auth_header:
#                     token = auth_header.split(' ')[1]
#                     if token != '12345678':
#                         raise ValueError('Authorization failed.')
#         except Exception as e:
#             return "401 Unauthorized\n{}\n\n".format(e), 401

if __name__ == '__main__':
    # app.run()
    print(544)
