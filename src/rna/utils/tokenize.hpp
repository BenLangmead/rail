//
//  tokenize.hpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#ifndef tokenize_hpp
#define tokenize_hpp

#include <string>
#include <sstream>
#include <limits>

namespace rail {

/**
 * Split string s according to given delimiters.  Mostly borrowed
 * from C++ Programming HOWTO 7.3.
 */
template<typename T>
static inline void tokenize(
	const std::string& s,
	const std::string& delims,
	T& ss,
	size_t max = std::numeric_limits<size_t>::max())
{
	//string::size_type lastPos = s.find_first_not_of(delims, 0);
	std::string::size_type lastPos = 0;
	std::string::size_type pos = s.find_first_of(delims, lastPos);
	while (std::string::npos != pos || std::string::npos != lastPos) {
		ss.push_back(s.substr(lastPos, pos - lastPos));
		lastPos = s.find_first_not_of(delims, pos);
		pos = s.find_first_of(delims, lastPos);
		if(ss.size() == (max - 1)) {
			pos = std::string::npos;
		}
	}
}

template<typename T>
static inline void tokenize(const std::string& s, char delim, T& ss) {
	std::string token;
	std::istringstream iss(s);
	while(getline(iss, token, delim)) {
		ss.push_back(token);
	}
}

}  // namespace rail
#endif /* tokenize_hpp */
