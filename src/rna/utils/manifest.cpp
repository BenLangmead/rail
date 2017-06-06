//
//  manifest.cpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#include <fstream>
#include <vector>
#include <stdexcept>
#include "manifest.hpp"
#include "tokenize.hpp"

namespace rail {

void labels_and_ids(
	const std::string& manifest_fn,
	std::map<int, std::string>& id_to_str,
	std::map<std::string, int>& str_to_id)
{
	std::ifstream infile(manifest_fn.c_str());
	std::vector<std::string> toks;
	if(infile.is_open()) {
		int i = 0;
		for(std::string line; getline(infile, line ); ) {
			if(line.empty()) {
				continue;
			}
			toks.clear();
			tokenize(line, '\t', toks);
			if(toks.size() > 5) {
				std::ostringstream oss;
				oss << "More than 5 fields for manifest line: '"
				    << line << "'";
				throw std::runtime_error(oss.str());
			}
			if(toks.back().empty()) {
				std::ostringstream oss;
				oss << "Bad sample label: '"
				    << toks.back() << "'";
				throw std::runtime_error(oss.str());
			}
			id_to_str.insert(make_pair(i, toks.back()));
			str_to_id.insert(make_pair(toks.back(), i));
			i++;
		}
	}
}

}  // namespace rail
