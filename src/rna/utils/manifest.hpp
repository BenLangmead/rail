//
//  manifest.hpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#ifndef manifest_hpp
#define manifest_hpp

#include <string>
#include <map>

namespace rail {

void labels_and_ids(
	const std::string& manifest_fn,
	std::map<int, std::string>& id_to_str,
	std::map<std::string, int>& str_to_id);

}  // namespace rail

#endif /* manifest_hpp */
