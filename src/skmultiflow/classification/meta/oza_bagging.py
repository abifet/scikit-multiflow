import copy as cp
from skmultiflow.classification.base import BaseClassifier
from skmultiflow.classification.lazy.knn_adwin import KNNAdwin
from skmultiflow.core.utils.utils import *


class OzaBagging(BaseClassifier):
    """ OzaBagging Classifier
    
    Oza Bagging is an ensemble learning method first introduced by Oza and 
    Russel's 'Online Bagging and Boosting'. They are an improvement of the 
    well known Bagging ensemble method for the batch setting, which in this 
    version can effectively handle data streams.
    
    For a traditional Bagging algorithm, adapted for the batch setting, we 
    would have M classifiers training on M different datasets, created by 
    drawing N samples from the N-sized training set with replacement.
    
    In the online context, since there is no training dataset, but a stream 
    of samples, the drawing of samples with replacement can't be trivially 
    executed. The strategy adopted by the Online Bagging algorithm is to 
    simulate this task by training each arriving sample K times, which is 
    drawn by the binomial distribution. Since we can consider the data stream 
    to be infinite, and knowing that with infinite samples the binomial 
    distribution tends to a Poisson(1) distribution, Oza and Russel found 
    that to be a good 'drawing with replacement'.
    
    Parameters
    ----------
    h: classifier (extension of the BaseClassifier)
        This is the ensemble classifier type, each ensemble classifier is going 
        to be a copy of the h classifier.
    
    ensemble_length: int
        The size of the ensemble, in other words, how many classifiers to train.
    
    Raises
    ------
    NotImplementedError: A few of the functions described here are not 
    implemented since they have no application in this context.
    
    ValueError: A ValueError is raised if the 'classes' parameter is 
    not passed in the first partial_fit call.
    
    Notes
    -----
    To choose the correct ensemble_length (a value too high or too low may 
    deteriorate performance) there are different techniques. One of them is 
    called 'The law of diminishing returns in ensemble construction' by Bonab 
    and Can. This theoretical framework claims, with experimental results, that 
    the optimal number of classifiers in an online ensemble method is equal to 
    the number of labels in the classification task. Thus we chose a default 
    value of 2, adapted to binary classification tasks.
    
    Examples
    --------
    >>> # Imports
    >>> from skmultiflow.classification.meta.oza_bagging import OzaBagging
    >>> from skmultiflow.classification.lazy.knn import KNN
    >>> from skmultiflow.data.generators.sea_generator import SEAGenerator
    >>> # Setting up the stream
    >>> stream = SEAGenerator(1, noise_percentage=6.7)
    >>> stream.prepare_for_use()
    >>> # Setting up the OzaBagging classifier to work with KNN classifiers
    >>> clf = OzaBagging(h=KNN(k=8, max_window_size=2000, leaf_size=30), ensemble_length=2)
    >>> # Keeping track of sample count and correct prediction count
    >>> sample_count = 0
    >>> corrects = 0
    >>> # Pre training the classifier with 200 samples
    >>> X, y = stream.next_instance(200)
    >>> clf = clf.partial_fit(X, y, classes=stream.get_classes())
    >>> for i in range(2000):
    ...     X, y = stream.next_instance()
    ...     pred = clf.predict(X)
    ...     clf = clf.partial_fit(X, y)
    ...     if pred is not None:
    ...         if y[0] == pred[0]:
    ...             corrects += 1
    ...     sample_count += 1
    >>> 
    >>> # Displaying the results
    >>> print(str(sample_count) + ' samples analyzed.')
    2000 samples analyzed.
    >>> print('OzaBagging classifier performance: ' + str(corrects / sample_count))
    OzaBagging classifier performance: 0.9645
    
    """

    def __init__(self, h=KNNAdwin(), ensemble_length=2):
        super().__init__()
        # default values
        self.ensemble = None
        self.ensemble_length = None
        self.classes = None
        self.h = h.reset()

        self.__configure(h, ensemble_length)

    def __configure(self, h, ensemble_length):
        self.ensemble_length = ensemble_length
        self.ensemble = [cp.deepcopy(h) for j in range(self.ensemble_length)]

    def reset(self):
        self.__configure(self.h, self.ensemble_length)

    def fit(self, X, y, classes=None, weight=None):
        raise NotImplementedError

    def partial_fit(self, X, y, classes=None, weight=None):
        """ partial_fit
         
        Partially fits the model, based on the X and y matrix.
                
        Since it's an ensemble learner, if X and y matrix of more than one 
        sample are passed, the algorithm will partial fit the model one sample 
        at a time.
        
        Each sample is trained by each classifier a total of K times, where K 
        is drawn by a Poisson(1) distribution.
        
        Parameters
        ----------
        X: Numpy.ndarray of shape (n_samples, n_features) 
            Features matrix used for partially updating the model.
            
        y: Array-like
            An array-like of all the class labels for the samples in X.
            
        classes: list 
            List of all existing classes. This is an optional parameter, except 
            for the first partial_fit call, when it becomes obligatory.

        weight: Array-like
            Instance weight. If not provided, uniform weights are assumed.

        Raises
        ------
        ValueError: A ValueError is raised if the 'classes' parameter is not 
        passed in the first partial_fit call, or if they are passed in further 
        calls but differ from the initial classes list passed.
        
        Returns
        _______
        OzaBagging
            self
        
        """
        r, c = get_dimensions(X)
        if self.classes is None:
            if classes is None:
                raise ValueError("The first partial_fit call should pass all the classes.")
            else:
                self.classes = classes

        if self.classes is not None and classes is not None:
            if set(self.classes) == set(classes):
                pass
            else:
                raise ValueError("The classes passed to the partial_fit function differ from those passed earlier.")

        self.__adjust_ensemble_size()

        for i in range(self.ensemble_length):
            k = np.random.poisson()
            if k > 0:
                for b in range(k):
                    self.ensemble[i].partial_fit(X, y, classes, weight)
        return self

    def __adjust_ensemble_size(self):
        if len(self.classes) != len(self.ensemble):
            if len(self.classes) > len(self.ensemble):
                for i in range(len(self.ensemble), len(self.classes)):
                    self.ensemble.append(cp.deepcopy(self.h))
                    self.ensemble_length += 1

    def predict(self, X):
        """ predict
        
        The predict function will average the predictions from all its learners 
        to find the most likely prediction for the sample matrix X.
        
        Parameters
        ----------
        X: Numpy.ndarray of shape (n_samples, n_features)
            A matrix of the samples we want to predict.
        
        Returns
        -------
        list
            A list with the label prediction for all the samples in X.
        
        """
        r, c = get_dimensions(X)
        probs = self.predict_proba(X)
        preds = []
        if probs is None:
            return None
        for i in range(r):
            preds.append(self.classes[probs[i].index(np.max(probs[i]))])
        return preds

    def predict_proba(self, X):
        """ predict_proba
        
        Predicts the probability of each sample belonging to each one of the 
        known classes.
        
        Parameters
        ----------
        X: Numpy.ndarray of shape (n_samples, n_features)
            A matrix of the samples we want to predict.
        
        Raises
        ------
        ValueError: A ValueError is raised if the number of classes in the h 
        learner differs from that of the ensemble learner.
        
        Returns
        -------
        numpy.ndarray
            An array of shape (n_samples, n_features), in which each outer entry is 
            associated with the X entry of the same index. And where the list in 
            index [i] contains len(self.classes) elements, each of which represents 
            the probability that the i-th sample of X belongs to a certain label.
        
        """
        probs = []
        r, c = get_dimensions(X)
        try:
            for i in range(self.ensemble_length):
                partial_probs = self.ensemble[i].predict_proba(X)
                if len(partial_probs[0]) != len(self.classes):
                    raise ValueError("The number of classes is different in the bagging algorithm and in the chosen learning algorithm.")

                if len(probs) < 1:
                    for n in range(r):
                        probs.append([0.0 for x in partial_probs[n]])

                for n in range(r):
                    for l in range(len(partial_probs[n])):
                        probs[n][l] += partial_probs[n][l]
        except ValueError:
            return None

        # normalizing probabilities
        if r > 1:
            total_sum = []
            for l in range(r):
                total_sum.append(np.sum(probs[l]))
        else:
            total_sum = [np.sum(probs)]
        aux = []
        for i in range(len(probs)):
            aux.append([x / total_sum[i] for x in probs[i]])
        return aux

    def score(self, X, y):
        raise NotImplementedError

    def get_info(self):
        return 'OzaBagging Classifier: h: ' + str(self.h) + \
               ' - ensemble_length: ' + str(self.ensemble_length)
