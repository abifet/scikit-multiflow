import numpy as np
from scipy import stats
from skmultiflow.filtering.base_transform import BaseTransform
from skmultiflow.core.utils.data_structures import FastBuffer
from skmultiflow.core.utils.utils import get_dimensions


class MissingValuesCleaner(BaseTransform):
    """ MissingValuesCleaner
    
    This is a transform object. It provides a simple way to replace missing 
    values in samples with another value, which can be chosen from a set of 
    replacing strategies.
    
    A missing value in a sample can be coded in many different ways, but the 
    most common one is to use numpy's NaN, that's why that is the default 
    missing value parameter.
    
    The user should choose the correct substitution strategy for his use 
    case, as each strategy has its pros and cons. The strategy can be chosen 
    from a set of predefined strategies, which are: 'zero', 'mean', 'median', 
    'mode', 'custom'.
    
    Parameters
    ----------
    missing_value: int, char (Default: numpy.nan)
        The way a missed value is coded in the matrices that are to be 
        transformed.
    
    strategy: string (Default: 'zero')
        The strategy adopted to find the missing value replacement. It can 
        be one of the following: 'zero', 'mean', 'median', 'mode', 'custom'.
    
    window_size: int (Default: 200)
        Defines the window size for the 'mean', 'median' and 'mode' strategies.
    
    new_value: int (Default: 1)
        This is the replacement value in case the chosen strategy is 'custom'.
        
    Examples
    --------
    >>> # Imports
    >>> import numpy as np
    >>> from skmultiflow .options.file_option import FileOption
    >>> from skmultiflow.data.file_stream import FileStream
    >>> from skmultiflow.filtering.base_filters import MissingValuesCleaner
    >>> # Setting up a stream
    >>> opt = FileOption('FILE', 'OPT_NAME', 'skmultiflow/datasets/covtype.csv', 'csv', False)
    >>> stream = FileStream(opt, -1, 1)
    >>> stream.prepare_for_use()
    >>> # Setting up the filter to substitute values -47 by the median of the 
    >>> # last 10 samples
    >>> filter = MissingValuesCleaner(-47, 'median', 10)
    >>> X, y = stream.next_instance(10)
    >>> X[9, 0] = -47
    >>> # We will use this list to keep track of values
    >>> list = []
    >>> # Iterate over the first 9 samples, to build a sample window
    >>> for i in range(9):
    ...     X_transf = filter.partial_fit_transform([X[i].tolist()])
    ...     list.append(X_transf[0][0])
    ...     print(X_transf)
    >>>
    >>> # Transform last sample. The first feature should be replaced by the list's 
    >>> # median value
    >>> X_transf = filter.partial_fit_transform([X[9].tolist()])
    >>> print(X_transf)
    >>> np.median(list)
    
    """

    def __init__(self, missing_value=np.nan, strategy='zero', window_size=200, new_value=1):
        super().__init__()
        #default_values
        self.missing_value = np.nan
        self.strategy = 'zero'
        self.window_size = 200
        self.window = None
        self.new_value = 1

        self.__configure(missing_value, strategy, window_size, new_value)

    def __configure(self, missing_value, strategy, window_size, new_value=1):
        if hasattr(missing_value, 'append'):
            self.missing_value = missing_value
        else:
            self.missing_value = [missing_value]
        self.strategy = strategy
        self.window_size = window_size
        self.new_value = new_value

        if strategy in ['mean', 'median', 'mode']:
            self.window = FastBuffer(max_size=window_size)

    def transform(self, X):
        """ transform
        
        Does the transformation process in the samples in X.
        
        Parameters
        ----------
        X: numpy.ndarray of shape (n_samples, n_features)
            The sample or set of samples that should be transformed.
        
        """
        r, c = get_dimensions(X)
        for i in range(r):
            for j in range(c):
                if X[i][j] in self.missing_value:
                    X[i][j] = self._get_substitute(j)

        return X

    def _get_substitute(self, column_index):
        """ _get_substitute
        
        Computes the replacement for a missing value.
        
        Parameters
        ----------
        column_index: int
            The index from the column where the missing value was found.
            
        Returns
        -------
        int or float
            The replacement.
        
        """
        if self.strategy == 'zero':
            return 0
        elif self.strategy == 'mean':
            if not self.window.isempty():
                return np.mean(np.array(self.window.get_queue())[:, column_index:column_index+1])
            else:
                return self.new_value
        elif self.strategy == 'median':
            if not self.window.isempty():
                return np.median(np.array(self.window.get_queue())[:, column_index:column_index+1].flatten())
            else:
                return self.new_value
        elif self.strategy == 'mode':
            if not self.window.isempty():
                return stats.mode(np.array(self.window.get_queue())[:, column_index:column_index+1].flatten())
            else:
                return self.new_value
        elif self.strategy == 'custom':
            return self.new_value

    def partial_fit_transform(self, X, y=None):
        """ partial_fit_transform
        
        Partially fits the model and then apply the transform to the data.
        
        Parameters
        ----------
        X: numpy.ndarray of shape (n_samples, n_features)
            The sample or set of samples that should be transformed.
            
        y: Array-like
            The true labels.
         
        Returns
        -------
        numpy.ndarray of shape (n_samples, n_features)
            The transformed data.
        
        """
        X = self.transform(X)
        if self.strategy in ['mean', 'median', 'mode']:
            self.window.add_element(X)

        return X

    def partial_fit(self, X, y=None):
        """ partial_fit
        
        Partial fits the model.
        
        Parameters
        ----------
        X: numpy.ndarray of shape (n_samples, n_features)
            The sample or set of samples that should be transformed.
            
        y: Array-like
            The true labels.
        
        Returns
        -------
        MissingValuesCleaner
            self
        
        """
        X = np.asarray(X)
        if self.strategy in ['mean', 'meadian', 'mode']:
            self.window.add_element(X)
        return self


    def get_info(self):
        return 'MissingValueCleaner: missing_value: ' + str(self.missing_value) + \
               ' - strategy: ' + self.strategy + \
               ' - window_size: ' + str(self.window_size) + \
               ' - new_value: ' + str(self.new_value)


