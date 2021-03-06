"""JupyterHub authenticator."""
import requests
import os
import json
from subprocess import check_output
from flask import request, redirect, abort
from IPython.utils.traitlets import Unicode, Int, List, Bool 

from nbgrader.html.formgrade import blueprint
from .base import BaseAuth


class HubAuth(BaseAuth):
    """Jupyter hub authenticator."""

    graders = List([], config=True, help="List of JupyterHub user names allowed to grade.")

    proxy_address = Unicode(config=True, help="Address of the configurable-http-proxy server.")
    def _proxy_address_default(self):
        return self._ip
    proxy_port = Int(8001, config=True, help="Port of the configurable-http-proxy server.")

    hub_address = Unicode(config=True, help="Address of the hub server.")
    def _hub_address_default(self):
        return self._ip
    hub_port = Int(8000, config=True, help="Port of the hub server.")
    
    hubapi_address = Unicode(config=True, help="Address of the hubapi server.")
    def _hubapi_address_default(self):
        return self._ip
    hubapi_port = Int(8081, config=True, help="Port of the hubapi server.")
    hubapi_cookie = Unicode("jupyter-hub-token", config=True, help="Name of the cookie used by JupyterHub")

    notebook_url_prefix = Unicode(None, config=True, allow_none=True, help="""
        Relative path of the formgrader with respect to the hub's user base
        directory.  No trailing slash. i.e. "Documents" or "Documents/notebooks". """)
    def _notebook_url_prefix_changed(self, name, old, new):
        self.notebook_url_prefix = new.strip('/')
    
    hub_base_url = Unicode(config=True, help="Base URL of the hub server.")
    def _hub_base_url_default(self):
        return 'http://{}:{}'.format(self.hub_address, self.hub_port)
    
    generate_hubapi_token = Bool(False, config=True, help="""Use `jupyterhub token` as a default
        for HubAuth.hubapi_token instead of $JPY_API_TOKEN.""")

    hub_db = Unicode(config=True, help="""Path to JupyterHub's database.  Only
        manditory if `generate_hubapi_token` is True.""")

    hubapi_token = Unicode(config=True, help="""JupyterHub API auth token.  
        Generated by running `jupyterhub token`.  If not explicitly set,
        nbgrader will use $JPY_API_TOKEN as the API token.""")
    def _hubapi_token_default(self):
        if self.generate_hubapi_token:
            return check_output([
                'jupyterhub', 'token', '--db={}'.format(self.hub_db)
                ]).decode('utf-8').strip()
        else:
            return os.environ.get('JPY_API_TOKEN', '')

    proxy_token = Unicode(config=True, help="""JupyterHub configurable proxy 
        auth token.  If not explicitly set, nbgrader will use 
        $CONFIGPROXY_AUTH_TOKEN as the API token.""")
    def _proxy_token_default(self):
        return os.environ.get('CONFIGPROXY_AUTH_TOKEN', '')

    remap_url = Unicode(config=True, help="""Suffix appened to 
        `HubAuth.hub_base_url` to form the full URL to the formgrade server.  By
        default this is '/hub/{{NbGraderConfig.course_id}}'.  Change this if you
        plan on running more than one formgrade server behind one JupyterHub
        instance.""")
    def _remap_url_default(self):
        return '/hub/nbgrader/' + self.parent.course_id
    def _remap_url_changed(self, name, old, new):
        self.remap_url = new.rstrip('/')

    def __init__(self, *args, **kwargs):
        super(HubAuth, self).__init__(*args, **kwargs)

        print('hello world')

        # Create base URLs for the hub and proxy.
        self._hubapi_base_url = 'http://{}:{}'.format(self.hubapi_address, self.hubapi_port)
        self._proxy_base_url = 'http://{}:{}'.format(self.proxy_address, self.proxy_port)

        # Register self as a route of the configurable-http-proxy and then
        # update the base_url to point to the new path.
        response = self._proxy_request('/api/routes' + self.remap_url, method='POST', body={
            'target': self._base_url
        })
        self.log.warn('Trying token "%s"' % self.proxy_token)
        print('Trying token "%s"' % self.proxy_token)
        if response.status_code != 201:
            self.log.warn('Error while trying to add JupyterHub route. {}: {}'.format(response.status_code, response.text))
            print('Error while trying to add JupyterHub route. {}: {}'.format(response.status_code, response.text))
        self._base_url = self.hub_base_url + self.remap_url

        # Redirect all formgrade request to the correct API method.
        self._app.register_blueprint(blueprint, static_url_path=self.remap_url + '/static', url_prefix=self.remap_url, url_defaults={'name': 'hub'})

    def authenticate(self):
        """Authenticate a request.
        Returns a boolean or flask redirect."""

        # If auth cookie doesn't exist, redirect to the login page with
        # next set to redirect back to the this page.
        if 'jupyter-hub-token' not in request.cookies:
            return redirect(self.hub_base_url + '/hub/login?next=' + self.hub_base_url + self.remap_url)
        cookie = request.cookies[self.hubapi_cookie]

        # Check with the Hub to see if the auth cookie is valid.
        response = self._hubapi_request('/hub/api/authorizations/cookie/' + self.hubapi_cookie + '/' + cookie)
        if response.status_code == 200:

            #  Auth information recieved.
            data = response.json()
            if 'user' in data:
                user = data['user']

                # Check if the user name is registered as a grader.
                if user in self.graders:
                    self._user = user
                    return True
                else:
                    self.log.warn('Unauthorized user "%s" attempted to access the formgrader.' % user)
            else:
                self.log.warn('Malformed response from the JupyterHub auth API.')
                abort(500, "Failed to check authorization, malformed response from Hub auth.")
        elif response.status_code == 403:
            self.log.error("I don't have permission to verify cookies, my auth token may have expired: [%i] %s", response.status_code, response.reason)
            abort(500, "Permission failure checking authorization, I may need to be restarted")
        elif response.status_code >= 500:
            self.log.error("Upstream failure verifying auth token: [%i] %s", response.status_code, response.reason)
            abort(502, "Failed to check authorization (upstream problem)")
        elif response.status_code >= 400:
            self.log.warn("Failed to check authorization: [%i] %s", response.status_code, response.reason)
            abort(500, "Failed to check authorization")
        else:
            # Auth invalid, reauthenticate.
            return redirect(self.hub_base_url + '/hub/login?next=' + self.hub_base_url + self.remap_url)
        return False

    def notebook_server_exists(self):
        """Does the notebook server exist?"""
        return True

    def get_notebook_url(self, relative_path):
        """Gets the notebook's url."""
        if self.notebook_url_prefix is not None:
            relative_path = self.notebook_url_prefix + '/' + relative_path
        return self.hub_base_url + "/user/{}/notebooks/{}".format(
            self._user,
            relative_path)

    def _hubapi_request(self, *args, **kwargs):
        return self._request('hubapi', *args, **kwargs)

    def _proxy_request(self, *args, **kwargs):
        return self._request('proxy', *args, **kwargs)

    def _request(self, service, relative_path, method='GET', body=None):
        base_url = getattr(self, '_%s_base_url' % service)
        token = getattr(self, '%s_token' % service)

        data = body
        if isinstance(data, (dict,)):
            data = json.dumps(data)

        return requests.request(method, base_url + relative_path, headers={
            'Authorization': 'token %s' % token
        }, data=data)
