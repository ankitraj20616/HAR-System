import unittest

from shared.labels import CANONICAL_ACTIVITIES, CANONICAL_EVENTS, ActivityLabel, map_activity_label
from shared.topics import (
    ACTIVITY,
    ALL_TOPICS,
    EVENT,
    FEEDBACK,
    SENSOR_PREDICTION,
    SENSOR_RAW,
    VIDEO_PREDICTION,
    policy_for,
)


class LabelAndTopicTests(unittest.TestCase):
    def test_external_labels_map_to_canonical_vocabulary(self):
        self.assertEqual(map_activity_label("walking upstairs"), ActivityLabel.WALKING)
        self.assertEqual(map_activity_label("upstairs"), ActivityLabel.WALKING)
        self.assertEqual(map_activity_label("downstairs"), ActivityLabel.WALKING)
        self.assertEqual(map_activity_label("laying"), ActivityLabel.LYING)
        self.assertEqual(map_activity_label("running"), ActivityLabel.EXERCISING)

    def test_unknown_input_maps_to_unknown(self):
        self.assertEqual(map_activity_label("invented-label"), ActivityLabel.UNKNOWN)
        self.assertEqual(map_activity_label(None), ActivityLabel.UNKNOWN)

    def test_topics_are_unique_and_have_explicit_delivery_policy(self):
        self.assertEqual(
            ALL_TOPICS,
            {
                "har/sensor/raw",
                "har/sensor/prediction",
                "har/video/prediction",
                "har/activity",
                "har/event",
                "har/feedback",
            },
        )
        self.assertEqual(policy_for(SENSOR_RAW).qos, 0)
        for topic in (SENSOR_PREDICTION, VIDEO_PREDICTION, ACTIVITY, EVENT, FEEDBACK):
            with self.subTest(topic=topic):
                self.assertEqual(policy_for(topic).qos, 1)
                self.assertFalse(policy_for(topic).retain)

    def test_canonical_vocabularies_are_exact(self):
        self.assertEqual(
            CANONICAL_ACTIVITIES,
            ("WALKING", "SITTING", "STANDING", "LYING", "EXERCISING", "UNKNOWN"),
        )
        self.assertEqual(CANONICAL_EVENTS, ("FALL", "INACTIVITY", "ABNORMAL_PATTERN"))

    def test_unknown_topic_is_rejected(self):
        with self.assertRaises(ValueError):
            policy_for("har/typo")


if __name__ == "__main__":
    unittest.main()
