//
//  rail_rna_align.hpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#ifndef rail_rna_align_hpp
#define rail_rna_align_hpp

#include <iostream>

namespace rail {

extern void rail_rna_align_step(
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
	bool no_polyA);

}  // namespace rail

#endif /* rail_rna_align_hpp */
