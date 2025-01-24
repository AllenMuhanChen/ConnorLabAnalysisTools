import bisect
import os
from dataclasses import dataclass

from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_marker_channels
from clat.intan.spike_file import fetch_spike_tstamps_from_file


@dataclass
class OneFileParser:
    import os
    import bisect

    def parse(self, intan_file_path: str):
        '''
        filtered_spikes_by_channel_by_task_id: Dict[taskId, Dict[Channel, Responses]].
        '''
        spike_path = os.path.join(intan_file_path, "spike.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        spike_tstamps_by_channel, sample_rate = fetch_spike_tstamps_from_file(spike_path)
        stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path, false_negative_correction_duration=2)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(notes_path, stim_epochs_from_markers,
                                                                   require_trial_complete=False)

        filtered_spikes_by_channel_by_task_id = {}
        epoch_start_stop_times_by_task_id = {}

        # Ensure all timestamps are sorted if not already sorted
        for channel, tstamps in spike_tstamps_by_channel.items():
            spike_tstamps_by_channel[channel] = sorted(tstamps)

        for task_id, epoch_indices in epochs_for_task_ids.items():
            print(f"Epoching task_id: {task_id}")
            filtered_spikes_for_channels = {}

            for channel, tstamps in spike_tstamps_by_channel.items():
                # Using binary search to find the range of timestamps within the current epoch
                start_index = bisect.bisect_left(tstamps, epoch_indices[0] / sample_rate)
                end_index = bisect.bisect_right(tstamps, epoch_indices[1] / sample_rate)
                # Extract the timestamps that fall within the epoch
                passed_filter = tstamps[start_index:end_index]
                filtered_spikes_for_channels[channel] = passed_filter

            epoch_start_seconds = epoch_indices[0] / sample_rate
            epoch_end_seconds = epoch_indices[1] / sample_rate
            epoch_start_stop_times_by_task_id[task_id] = (epoch_start_seconds, epoch_end_seconds)
            filtered_spikes_by_channel_by_task_id[task_id] = filtered_spikes_for_channels

        return filtered_spikes_by_channel_by_task_id, epoch_start_stop_times_by_task_id, sample_rate


