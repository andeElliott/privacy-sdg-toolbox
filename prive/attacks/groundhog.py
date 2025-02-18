"""
Parent class for launching a membership inference attack on the output of a 
generative model.
"""
# Type checking stuff
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..datasets import DataDescription # for typing # TODO: define this class
    from ..threat_models import ThreatModel # for typing
    from .set_classifiers import SetClassifier # for typing

# Real imports
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from .base_classes import Attack

# TODO: Remove this import potentially?
from warnings import simplefilter
simplefilter('ignore', category=FutureWarning)
simplefilter('ignore', category=DeprecationWarning)


class Groundhog(Attack):
    """
    Implementation of Stadler et al. (2022) attack

    Parent class for membership inference attack on the output of a 
    generative model using a classifier.

    Attributes
    ----------
    classifier : SetClassifier
        Instance of a SetClassifier that will be used as the classification
        model for this attack.
    data_description : DataDescription
        Instance of DataDescription that describes that data that the attack
        will be performed on.
    trained : bool
        Indicates whether or not the attack has been trained on some data.

    """

    def __init__(self,
                 classifier: SetClassifier,
                 data_description: DataDescription):
        """
        Initialise a Groundhog attack from a threat model, classifier and
        data description.

        Parameters
        ----------
        classifier : SetClassifier
            SetClassifier to set for attack.
        data_description : DataDescription
            DataDescription to set for attack.

        """
        self.classifier = classifier
        self.data_description = data_description

        self.trained = False

        self.__name__ = f'{self.classifier.__class__.__name__}Groundhog'

    def train(self,
              threat_model: ThreatModel = None, # TODO: should we specify targeted, static data?
              num_samples: int = 100,
              synthetic_datasets: list[Dataset] = None,
              labels: list[int] = None):
        """
        Train the attack classifier on a labelled set of datasets. The datasets
        will either be generated from threat_model or need to be provided.

        Parameters
        ----------
        threat_model : ThreatModel
            Threat model to use to generate training samples if synthetic_datasets
            or labels are not given.
        num_samples : int, optional
            Number of datasets to generate using threat_model if
            synthetic_datasets or labels are not given. The default is 100.
        synthetic_datasets : list[Dataset], optional
            List of datasets.Dataset objects. If not provided, threat_model
            will be used to generate a new batch of synthetic_datasets and labels.
            The default is None.
        labels : list[int], optional
            Labels for the given synthetic_datasets. A label of 1 indicates that
            the target row is present in the data. The default is None.

        """
        # Generate data from threat model if no data is provided
        if synthetic_datasets is None or labels is None:
            synthetic_datasets, labels = threat_model.generate_training_samples(num_samples)

        # Fit the classifier to the data
        self.classifier.fit(synthetic_datasets, labels)

        self.trained = True

    def attack(self, datasets: list[Dataset]) -> list[int]:
        """
        Make a guess about the target's membership in the training data that was
        used to produce each dataset in datasets.

        Parameters
        ----------
        datasets : list[Dataset]
            List of (synthetic) datasets to make a guess for.

        Returns
        -------
        list[int]
            Binary guesses for each dataset. A guess of 1 at index i indicates
            that the attack believes that the target was present in dataset i.

        """
        assert self.trained, 'Attack must first be trained.'

        return np.round(self.classifier.predict(datasets), 0)

    def _make_guess(self, datasets: list[Dataset]) -> int:
        """
        Make a guess for a single dataset about the presence of the target in
        the training data that generated the dataset

        """
        return np.round(self.classifier.predict(datasets), 0).astype(int)[0]

    # TODO: Fix arg type, add type hints and reformat docstring
    def attack_score(self, synT: list[Dataset], secret: list[int]) -> list[float]:
        """
        Calculate classifier's raw probability about the presence of the target.
        Output is a probability in [0, 1].

        Parameters
        ----------
        synT : list[Dataset]
            List of (synthetic) datasets to make a guess for.
        secret : list[int]
            List indicating the truth about the target's presence in the
            (training data of) the corresponding dataset in synT.

        Returns
        -------
        list[float]
            List of probabilities corresponding to attacker's guess about the truth.

        """
        # None of this will work
        assert self.trained, 'Attack must first be trained.'
        if self.FeatureSet is not None:
            synT = np.stack([self.FeatureSet.extract(s) for s in synT])
        else:
            if isinstance(synT[0], pd.DataFrame):
                synT = np.stack([convert_df_to_array(s, self.metadata).flatten() for s in synT])
            else:
                synT = np.stack([s.flatten() for s in synT])

        probs = self.Classifier.predict_proba(synT)

        return [p[s] for p,s in zip(probs, secret)]
