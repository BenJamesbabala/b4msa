# Copyright 2016 Ranyart R. Suarez (https://github.com/RanyartRodrigo) and Mario Graff (https://github.com/mgraffg)
# with collaborations of Eric S. Tellez

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from sklearn.svm import LinearSVC
# from b4msa.textmodel import TextModel
import numpy as np
from b4msa.utils import read_data_labels, read_data
from gensim.matutils import corpus2csc
from sklearn import preprocessing


class SVC(object):
    def __init__(self, model):
        self.svc = LinearSVC()
        self.model = model
        self.num_terms = -1

    def fit(self, X, y):
        X = corpus2csc(X).T
        self.num_terms = X.shape[1]
        self.le = preprocessing.LabelEncoder()
        self.le.fit(y)
        y = self.le.transform(y)
        self.svc.fit(X, y)
        return self

    def predict(self, Xnew):
        Xnew = corpus2csc(Xnew, num_terms=self.num_terms).T
        ynew = self.svc.predict(Xnew)
        return self.le.inverse_transform(ynew)

    def predict_text(self, text):
        y = self.predict([self.model[text]])
        return y[0]

    def fit_file(self, fname, get_tweet='text',
                 get_klass='klass', maxitems=1e100):
        X, y = read_data_labels(fname, get_klass=get_klass,
                                get_tweet=get_tweet, maxitems=maxitems)
        self.fit([self.model[x] for x in X], y)
        return self

    def predict_file(self, fname, get_tweet='text', maxitems=1e100):
        hy = [self.predict_text(x)
              for x in read_data(fname, get_tweet=get_tweet,
                                 maxitems=maxitems)]
        return hy

    @classmethod
    def predict_kfold(cls, fname, n_folds=10, seed=0, conf=None,
                      get_tweet='text',
                      get_klass='klass',
                      maxitems=1e100):
        from sklearn import cross_validation
        from b4msa.textmodel import TextModel
        
        try:
            from tqdm import tqdm
        except ImportError:
            def tqdm(x, **kwargs):
                return x

        X, y = read_data_labels(fname, get_klass=get_klass,
                                get_tweet=get_tweet, maxitems=maxitems)
        le = preprocessing.LabelEncoder().fit(y)
        y = np.array(le.transform(y))
        hy = np.zeros(len(y), dtype=np.int)
        xv = cross_validation.StratifiedKFold(y,
                                              n_folds=n_folds,
                                              shuffle=True,
                                              random_state=seed)

        if conf is None:
            for tr, ts in tqdm(xv, total=n_folds):
                t = TextModel([X[x] for x in tr])
                m = cls(t).fit([t[X[x]] for x in tr], [y[x] for x in tr])
                hy[ts] = np.array(m.predict([t[X[x]] for x in ts]))
            return le.inverse_transform(hy)
        else:
            for tr, ts in tqdm(xv, total=n_folds):
                t = TextModel([X[x] for x in tr], **conf)
                m = cls(t).fit([t[X[x]] for x in tr], [y[x] for x in tr])
                hy[ts] = np.array(m.predict([t[X[x]] for x in ts]))
            # return le.inverse_transform(hy)
            return (np.array(hy) == np.array(y)).sum()/len(y)

    @classmethod
    def predict_kfold_params(cls, fname, n_folds=10, n_params=10):
        from b4msa.params import ParameterSelection

        class func(object):
            def __init__(self, fname, n_folds):
                self.n_folds = n_folds
                self.fname = fname

            def F(self, conf):
                r = cls.predict_kfold(self.fname, self.n_folds, conf=conf)
                return r

        f = func(fname, n_folds)
        params = ParameterSelection().search(f.F,
                                             bsize=n_params,
                                             hill_climb=False)
        return params

