//
//  rail_rna_align.cpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#include <map>
#include <stdexcept>
#include <sstream>
#include "rail_rna_align.hpp"
#include "hadoop_util.hpp"
#include "manifest.hpp"
#include "file_util.hpp"

namespace rail {

void rail_rna_align_step(
	FILE *in,
	FILE *out,
	const std::string& bt2_exe,
	const std::string& bt2_idx,
	const std::string& manifest,
	const std::string& bt2_args,
	int bin_sz,
	bool verbose,
	bool exon_diffs,
	bool exon_ivals,
	double report_mult,
	int min_exon_len,
	int search_filter,
	int min_readlet_len,
	int max_readlen_len,
	int readlet_ival,
	double cap_mult,
	bool drop_deletes,
	int gzip_level,
	const std::string& scratch,
	int index_count,
	bool bam_by_chr,
	int tie_margin,
	bool no_realign,
	bool no_polyA)
{
	if(!exists(manifest)) {
		std::ostringstream oss;
		oss << "Manifest file '" << manifest << "' does not exist";
		throw std::runtime_error(oss.str());
	}
	if(!exists_and_executable(bt2_exe)) {
		std::ostringstream oss;
		oss << "Bowtie 2 exe '" << bt2_exe << "' does not exist or is not executable";
		throw std::runtime_error(oss.str());
	}
	
	std::map<int, std::string> id_to_str;
	std::map<std::string, int> str_to_id;
	labels_and_ids(manifest, id_to_str, str_to_id);
	
	// Get task partition to pass to align_reads_delegate.py
	std::string part = get_task_partition();
	
	std::string temp_dir = make_temp_dir(scratch);

	std::string align_fn = temp_dir + "/first_pass_reads.temp.gz";
	std::string other_reads_fn = temp_dir + "/other_reads.temp.gz";
	std::string second_pass_fn = temp_dir + "/first_pass_reads.temp.gz";
	
	bool nothing_doing = true;
	int remaining_seq_size = std::max(min_exon_len - 1, 1);
	
	return;
}

#ifdef rail_rna_align_test
int main(void) {
	return 0;
}
#endif // rail_rna_align_hpp

}  // namespace rail
