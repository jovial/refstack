/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

(function () {
    'use strict';

    angular
        .module('refstackApp')
        .factory('getVersionList', ['$http', 'refstackApiUrl', function($http, refstackApiUrl) {
            return function(gl_type) {
                var content_url = refstackApiUrl + '/targets/' + gl_type + "/versions";
                return $http.get(content_url).then(function(response) {
                    var data = response.data;
                    data.sort();
                    data.reverse();
                    return data;
                    });
            };
        }]);

    angular
        .module('refstackApp')
        .factory('getPlatformMap', ['$http', 'refstackApiUrl', function($http, refstackApiUrl) {
            return function() {
                var content_url = refstackApiUrl + '/targets';
                return $http.get(content_url).then(function(response) {
                    var data = response.data;
                    var platformMap = {};
                    for (var i in data) {
                        var property = data[i];
                        var id = property["id"];
                        var description = property["description"];
                        platformMap[id] = description;
                    }

                    return platformMap;
                });
            };
        }]);

    angular
        .module('refstackApp')
        .factory('invertObject', [function() {
            return function(object) {
                var result = {};
                for (var key in object) {
                    var value = object[key];
                    result[value] = key;
                }
                return result;
            };
        }]);

})();
